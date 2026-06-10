import { authHeader, useAuth } from "./auth";

const BASE = "";

function handleUnauth() {
  useAuth.getState().logout();
  window.location.href = "/login";
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path, { headers: authHeader() });
  if (res.status === 401) { handleUnauth(); throw new Error("Session expired"); }
  if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(body),
  });
  if (res.status === 401) { handleUnauth(); throw new Error("Session expired"); }
  if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
  return res.json();
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(body),
  });
  if (res.status === 401) { handleUnauth(); throw new Error("Session expired"); }
  if (!res.ok) throw new Error(`PATCH ${path}: ${res.status}`);
  return res.json();
}

// ── Runs ──────────────────────────────────────────────────────────────────────

export interface Run {
  id: number;
  repo_name: string;
  pr_number: number | null;
  status: string;
  started_at: string;
  total_findings: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export interface RunsResponse {
  runs: Run[];
}

export const getRuns = (limit = 20, status = "completed") =>
  get<RunsResponse>(`/v1/runs?limit=${limit}&status=${status}`);

export interface Finding {
  id: number;
  rule_id: string;
  severity: string;
  category: string | null;
  file_path: string;
  line_number: number | null;
  line_start: number;
  message: string;
  explanation_text: string | null;
  model_name: string | null;
  confidence: number;
  tool: string | null;
  taint_source: string | null;
  taint_path: string | null;
  taint_confidence: number | null;
  triage_verdict: string | null;
  triage_reasoning: string | null;
  triage_confidence_delta: number | null;
  ground_truth: string | null;
  exploit_tier: string | null;
  exploit_proof: string | null;
  exploit_evidence: string | null;
  exploit_duration_seconds: number | null;
}

export interface FindingsResponse {
  findings: Finding[];
  total: number;
}

export const getFindings = (runId: number, params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return get<FindingsResponse>(`/v1/runs/${runId}/findings${qs}`);
};

export interface RunStats {
  run_id: number;
  repo_name: string;
  status: string;
  total_findings: number;
  high: number;
  medium: number;
  low: number;
  avg_latency_ms: number;
  total_cost_usd: number;
}

export const getStats = (runId: number) =>
  get<RunStats>(`/v1/runs/${runId}/stats`);

export interface ComplianceData {
  owasp: Record<string, { count: number; severity: string }>;
  overall_score: number;
}

export const getCompliance = (runId: number) =>
  get<{ success: boolean } & ComplianceData>(`/v1/runs/${runId}/compliance`);

export interface AutofixResult {
  finding_id: number;
  run_id: number;
  rule_id: string;
  patch: string;
  confidence: number;
  explanation: string;
  valid: boolean;
  validation_note: string;
}

export const getAutofix = (runId: number, findingId: number) =>
  get<AutofixResult>(`/v1/runs/${runId}/findings/${findingId}/autofix`);

export interface SupplyChainResponse {
  success: boolean;
  run_id: number;
  summary: { total: number; high_risk: number; medium_risk: number; low_risk: number; total_cves: number };
  dependencies: Dependency[];
}

export interface Dependency {
  id: number;
  name: string;
  version: string;
  ecosystem: string;
  risk_score: number;
  risk_level: string;
  cve_count: number;
  cve_ids: string[];
  stars: number | null;
  last_commit_days: number | null;
  contributors: number | null;
  archived: boolean | null;
  license: string | null;
  sbom_purl: string | null;
}

export const getSupplyChain = (runId: number, riskLevel?: string) => {
  const qs = riskLevel ? `?risk_level=${riskLevel}` : "";
  return get<SupplyChainResponse>(`/v1/runs/${runId}/supply-chain${qs}`);
};

export const getSbom = (runId: number) =>
  get<{ success: boolean; run_id: number; sbom: unknown }>(`/v1/runs/${runId}/sbom`);

export interface TrendPoint {
  date: string;
  total: number;
  high: number;
  medium: number;
  low: number;
}

export const getTrends = () =>
  get<{ runs: Run[] }>("/v1/runs?limit=30&status=completed").then((r) =>
    r.runs
      .filter((run) => run.status === "completed")
      .slice(0, 10)
      .reverse()
      .map((run) => ({
        date: new Date(run.started_at).toLocaleDateString(),
        total: run.total_findings,
        high: run.high_count,
        medium: run.medium_count,
        low: run.low_count,
      }))
  );

// ── Scans ─────────────────────────────────────────────────────────────────────

export interface ScanJob {
  job_id: string;
  status: string;
  run_id?: number;
  message?: string;
}

export const submitScan = (targetDir: string, repoName: string) =>
  post<ScanJob>("/v1/scans", { target_dir: targetDir, repo_name: repoName });

export const getScanStatus = (jobId: string) =>
  get<ScanJob>(`/v1/scans/${jobId}`);

export const submitIacScan = (targetDir: string, repoName: string) =>
  post<ScanJob>("/v1/scans/iac", { target_dir: targetDir, repo_name: repoName });

export const submitScaScan = (targetDir: string, repoName: string) =>
  post<ScanJob>("/v1/scans/sca", { target_dir: targetDir, repo_name: repoName });

export const submitSecretsScan = (targetDir: string, repoName: string) =>
  post<ScanJob>("/v1/scans/secrets", { target_dir: targetDir, repo_name: repoName });

// ── PR Risk ───────────────────────────────────────────────────────────────────

export interface PrRisk {
  run_id: number;
  score: number;
  band: "green" | "yellow" | "red";
  inputs: Record<string, number>;
  contributions: Record<string, number>;
  explainer: string[];
}

export const getPrRisk = (runId: number) =>
  get<PrRisk>(`/v1/runs/${runId}/pr-risk`);

// ── Cost-Benefit ──────────────────────────────────────────────────────────────

export interface CostBenefit {
  analysis_cost_usd: number;
  hours_saved: number;
  dev_cost_saved_usd: number;
  roi_multiplier: string;
  cost_per_finding: number;
  total_findings: number;
}

export const getCostBenefit = (runId: number) =>
  get<{ success: boolean } & CostBenefit>(`/v1/runs/${runId}/cost-benefit`);

// ── Review Bottleneck ─────────────────────────────────────────────────────────

export interface ReviewBottleneck {
  median_time_to_first_review_hours: number;
  reviewer_load_gini: number;
  pct_merged_without_comment: number;
  top3_reviewer_share: number;
  stale_pr_count: number;
  total_commits_analyzed: number;
}

export const getReviewBottleneck = (runId: number) =>
  get<{ success: boolean } & ReviewBottleneck>(`/v1/runs/${runId}/review-bottleneck`);

// ── Second Opinion ────────────────────────────────────────────────────────────

export interface SecondOpinion {
  finding_id: number;
  primary_provider: string;
  primary_verdict: string;
  primary_reason: string;
  secondary_provider: string;
  secondary_verdict: string;
  secondary_reason: string;
  agreement: boolean;
  confidence_delta: number;
  skipped_reason: string | null;
  latency_ms: number;
}

export const postSecondOpinion = (findingId: number) =>
  post<SecondOpinion>(`/v1/findings/${findingId}/second-opinion`, {});

// ── API Keys ──────────────────────────────────────────────────────────────────

export interface ApiKey {
  id: number;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
}

export const getApiKeys = () =>
  get<ApiKey[]>("/v1/auth/api-keys");

export const createApiKey = (name: string) =>
  post<{ key: string; prefix: string; id: number }>("/v1/auth/api-keys", { name });

export const deleteApiKey = async (id: number) => {
  const res = await fetch(`/v1/auth/api-keys/${id}`, {
    method: "DELETE",
    headers: authHeader(),
  });
  if (!res.ok) throw new Error(`DELETE api-key ${id}: ${res.status}`);
};

export const deleteAccount = async () => {
  const res = await fetch("/v1/auth/users/me", {
    method: "DELETE",
    headers: authHeader(),
  });
  if (!res.ok) throw new Error(`DELETE account: ${res.status}`);
};

// ── Summary & Attestation ─────────────────────────────────────────────────────

export interface RunSummary {
  success: boolean;
  run_id: number;
  summary_markdown: string;
  stats: { total: number; high: number; medium: number; low: number };
}

export const getRunSummary = (runId: number) =>
  get<RunSummary>(`/v1/runs/${runId}/summary`);

export interface AttestationBundle {
  run_id: number;
  key_id: string | null;
  created_at: string;
  signature_algorithms: string[];
  post_quantum: boolean;
  signature_valid: boolean;
  bundle: unknown;
}

export const getAttestation = (runId: number) =>
  get<AttestationBundle>(`/v1/runs/${runId}/attestation`);

// ── Risk Map ──────────────────────────────────────────────────────────────────

export interface FileRiskScore {
  file_path: string;
  score: number;
  features: Record<string, number>;
  contributions: Record<string, number>;
}

export interface RiskMapResponse {
  run_id: number;
  cached: boolean;
  total_files: number;
  files: FileRiskScore[];
}

export const getRiskMap = (runId: number, refresh = false) =>
  get<RiskMapResponse>(`/v1/runs/${runId}/risk-map${refresh ? "?refresh=true" : ""}`);

// ── AI Detection ──────────────────────────────────────────────────────────────

export interface AIDetectFile {
  file_path: string;
  score: number;
  flagged: boolean;
}

export interface AIDetectResponse {
  success: boolean;
  total_files: number;
  flagged_files: number;
  flagged_percentage: number;
  files: AIDetectFile[];
}

export const postAIDetection = (target: string, threshold = 0.7) =>
  post<AIDetectResponse>("/v1/scans/ai-detection", { target, threshold });

// ── Vulnerabilities (Phase 0 / Phase 1) ───────────────────────────────────────

export type VulnStatus =
  | "detected" | "confirmed" | "assigned" | "in_progress"
  | "fixed" | "verified" | "regressed" | "dismissed";

export interface Vulnerability {
  id: number;
  fingerprint: string;
  short_id: string;
  canonical_rule_id: string;
  file_path: string;
  status: VulnStatus;
  owner: string | null;
  severity: string;
  category: string | null;
  message: string | null;
  first_seen_run_id: number | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VulnerabilityListResponse {
  total: number;
  limit: number;
  offset: number;
  vulnerabilities: Vulnerability[];
}

export interface VulnFindingEvent {
  id: number;
  run_id: number;
  run_started_at: string;
  repo_name: string;
  canonical_severity: string;
  category: string | null;
  message: string;
  file_path: string;
  line_number: number | null;
  evidence: Record<string, unknown> | null;
  triage_verdict: string | null;
  triage_reasoning: string | null;
  second_opinion_primary_verdict: string | null;
  second_opinion_secondary_verdict: string | null;
  second_opinion_agreement: boolean | null;
  confidence_score: number | null;
}

export interface VulnFindingsResponse {
  vulnerability_id: number;
  findings: VulnFindingEvent[];
}

export const getVulnerability = (shortId: string) =>
  get<Vulnerability>(`/v1/vulnerabilities/by/${shortId}`);

export const listVulnerabilities = (params?: {
  status?: string; severity?: string; rule?: string; owner?: string;
  limit?: number; offset?: number;
}) => {
  const qs = params ? "?" + new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)]))
  ).toString() : "";
  return get<VulnerabilityListResponse>(`/v1/vulnerabilities${qs}`);
};

export const getVulnFindings = (vulnId: number) =>
  get<VulnFindingsResponse>(`/v1/vulnerabilities/${vulnId}/findings`);

export const patchVulnStatus = (vulnId: number, status: VulnStatus) =>
  patch<Vulnerability>(`/v1/vulnerabilities/${vulnId}/status`, { status });

export const patchVulnOwner = (vulnId: number, owner: string | null) =>
  patch<Vulnerability>(`/v1/vulnerabilities/${vulnId}/owner`, { owner });

// ── Inbox (Phase 2) ───────────────────────────────────────────────────────────

export interface InboxResponse {
  regressions: Vulnerability[];
  stale_tps: Vulnerability[];
  disagreements: Vulnerability[];
  new_vulns: Vulnerability[];
  assigned_to_me: Vulnerability[];
  pr_vulns: Vulnerability[];
  total: number;
}

export const getInbox = (staleDays = 7) =>
  get<InboxResponse>(`/v1/inbox?stale_days=${staleDays}`);

export const bulkPatch = (body: {
  vuln_ids: number[];
  status?: VulnStatus;
  owner?: string;
  clear_owner?: boolean;
}) => post<{ updated: number; vuln_ids: number[] }>("/v1/inbox/bulk", body);

// ── Relationships (Phase 3) ────────────────────────────────────────────────────

export interface RelatedVuln {
  related_id: number;
  edge_type: "same_rule" | "same_file" | "taint_chain";
  score: number;
  short_id: string;
  canonical_rule_id: string;
  severity: string;
  status: VulnStatus;
  file_path: string;
  title: string | null;
}

export interface RelatedResponse {
  vuln_id: number;
  total: number;
  related: RelatedVuln[];
}

export interface RuleStats {
  canonical_rule_id: string;
  total: number;
  open: number;
  high: number;
  medium: number;
  low: number;
  files_affected: number;
  owners: number;
}

export interface SearchResult {
  q: string;
  vulns: Array<{ short_id: string; canonical_rule_id: string; severity: string; status: string; file_path: string; title: string | null }>;
  rules: Array<{ canonical_rule_id: string; open_count: number }>;
  authors: Array<{ owner: string; open_count: number }>;
}

export const getRelated = (vulnId: number) =>
  get<RelatedResponse>(`/v1/vulnerabilities/${vulnId}/related`);

export const getRuleStats = (ruleId: string) =>
  get<RuleStats>(`/v1/rules/${encodeURIComponent(ruleId)}/stats`);

export const searchObjects = (q: string, limit = 10) =>
  get<SearchResult>(`/v1/search?q=${encodeURIComponent(q)}&limit=${limit}`);

// ── Fleet (Phase 4) ───────────────────────────────────────────────────────────

export interface FleetRepoRow {
  repo_name: string;
  total_vulns: number;
  open_vulns: number;
  open_high: number;
  open_med: number;
  open_low: number;
  regressions: number;
  last_scan: string | null;
  total_scans: number;
}

export interface FleetResponse {
  org: {
    open_total: number;
    regressions: number;
    open_high: number;
    owners_with_open: number;
    repo_count: number;
  };
  repos: FleetRepoRow[];
}

export interface ComplianceRow {
  category: string;
  open_count: number;
  risk: "high" | "medium" | "none";
}

export interface ComplianceResponse {
  matrix: ComplianceRow[];
  total_open: number;
}

export interface StrideVuln {
  short_id: string;
  rule: string;
  severity: string;
  file: string;
  title: string | null;
}

export interface StrideRow {
  threat: string;
  count: number;
  risk: "high" | "medium" | "none";
  vulns: StrideVuln[];
}

export interface StrideResponse {
  repo_name: string;
  stride: StrideRow[];
  unclassified_count: number;
  total_open: number;
}

export const getFleet = (limit = 50) =>
  get<FleetResponse>(`/v1/fleet?limit=${limit}`);

export const getFleetCompliance = () =>
  get<ComplianceResponse>("/v1/fleet/compliance");

export const getStride = (repoName: string) =>
  get<StrideResponse>(`/v1/fleet/stride/${encodeURIComponent(repoName)}`);

// ── Workbench (Phase 5) ───────────────────────────────────────────────────────

export interface WbQueryParams {
  severity?: string;
  rule?: string;
  status?: string;
  file?: string;
  owner?: string;
  limit?: number;
  offset?: number;
}

export interface WbVulnRow {
  id: number;
  short_id: string;
  canonical_rule_id: string;
  severity: string;
  status: string;
  file_path: string;
  title: string | null;
  owner: string | null;
  first_seen_at: string | null;
  updated_at: string | null;
  finding_count: number;
}

export interface WbQueryResponse {
  total: number;
  limit: number;
  offset: number;
  results: WbVulnRow[];
}

export interface WbNLResponse extends WbQueryResponse {
  parsed: WbQueryParams;
}

export interface RulePerf {
  rule_id: string;
  fire_count: number;
  tp_count: number;
  fp_count: number;
  tp_rate: number | null;
  noise_ratio: number;
  labelled_count: number;
  gt_tp: number;
  gt_fp: number;
  gt_accuracy: number | null;
  avg_confidence: number;
  runs_seen: number;
  last_seen: string | null;
}

export interface AuditEvent {
  vuln_id: number | null;
  short_id: string | null;
  canonical_rule_id: string | null;
  severity: string | null;
  status: string | null;
  owner: string | null;
  file_path: string | null;
  repo_name: string;
  triage_verdict: string | null;
  confidence_score: number | null;
  event_at: string;
  event_type: string;
}

export interface LabelFinding {
  id: number;
  canonical_rule_id: string;
  canonical_severity: string;
  file_path: string;
  line_number: number | null;
  message: string;
  ground_truth: string | null;
  triage_verdict: string | null;
  confidence_score: number | null;
  repo_name: string;
  started_at: string;
}

export interface AttackPathNode {
  id: number;
  short_id: string;
  rule: string;
  severity: string;
  status: string;
  file: string;
  hop: number;
}

export interface AttackPathEdge { from: number; to: number; score: number; }

export interface AttackPathResponse {
  root_vuln_id: number;
  depth: number;
  node_count: number;
  edge_count: number;
  nodes: AttackPathNode[];
  edges: AttackPathEdge[];
}

export const wbQuery = (params: WbQueryParams = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)]))
  ).toString();
  return get<WbQueryResponse>(`/v1/workbench/query${qs ? "?" + qs : ""}`);
};

export const wbNLQuery = (q: string, useLLM = false) =>
  post<WbNLResponse>("/v1/workbench/nl-query", { q, use_llm: useLLM });

export const getRulePerformance = (limit = 50) =>
  get<{ total: number; rules: RulePerf[] }>(`/v1/workbench/rule-performance?limit=${limit}`);

export const getAuditLog = (limit = 100, repo?: string) =>
  get<{ total: number; events: AuditEvent[] }>(
    `/v1/workbench/audit-log?limit=${limit}${repo ? `&repo=${encodeURIComponent(repo)}` : ""}`
  );

export const getLabels = (params: { runId?: number; unlabelled_only?: boolean; limit?: number; offset?: number } = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)]))
  ).toString();
  return get<{ total: number; limit: number; offset: number; findings: LabelFinding[] }>(
    `/v1/workbench/labels${qs ? "?" + qs : ""}`
  );
};

export const setLabel = (findingId: number, groundTruth: string, reasoning = "") =>
  patch<{ finding_id: number; ground_truth: string; updated: boolean }>(
    `/v1/workbench/labels/${findingId}`,
    { ground_truth: groundTruth, reasoning }
  );

export const getAttackPaths = (vulnId: number, depth = 3) =>
  get<AttackPathResponse>(`/v1/workbench/attack-paths/${vulnId}?depth=${depth}`);

// ── Trust (Phase 6) ───────────────────────────────────────────────────────────

export interface TrustCompliance {
  owasp_top10: "pass" | "warn" | "fail";
  cwe_top25:   "pass" | "warn" | "fail";
  overall:     "pass" | "warn" | "fail";
}

export interface TrustSignature {
  algorithm: string;
  signature: string;
  key_id:    string;
}

export interface TrustPosture {
  repo_name:                 string;
  scan_count:                number;
  last_scan:                 string | null;
  first_scan:                string | null;
  freshness_days:            number | null;
  scan_frequency_per_week:   number | null;
  open_total:                number;
  open_high:                 number;
  open_med:                  number;
  open_low:                  number;
  fixed_total:               number;
  regressions:               number;
  compliance:                TrustCompliance;
  generated_at:              string;
  signature:                 TrustSignature | null;
  public_key_url:            string;
  attestation_url:           string;
}

export interface TrustPublicKey {
  kid:       string;
  algorithm: string;
  pem:       string;
}

export interface TrustAttestation {
  run_id:         number;
  repo_name:      string;
  key_id:         string | null;
  created_at:     string | null;
  bundle:         Record<string, unknown>;
  signature:      string | null;
  public_key_url: string;
}

// Public fetch (no auth header)
async function getPublic<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
  return res.json();
}

export const getTrustPosture = (repoName: string) =>
  getPublic<TrustPosture>(`/v1/trust/${encodeURIComponent(repoName)}`);

export const getTrustAttestation = (repoName: string) =>
  getPublic<TrustAttestation>(`/v1/trust/${encodeURIComponent(repoName)}/attestation`);

export const getTrustPublicKey = (repoName: string) =>
  getPublic<TrustPublicKey>(`/v1/trust/${encodeURIComponent(repoName)}/public-key`);
