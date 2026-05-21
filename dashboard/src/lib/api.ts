import { authHeader } from "./auth";

const BASE = "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path, { headers: authHeader() });
  if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
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

export const getRuns = (limit = 20) =>
  get<RunsResponse>(`/v1/runs?limit=${limit}`);

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
  get<{ runs: Run[] }>("/v1/runs?limit=30").then((r) =>
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
