import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

export const useRuns = (limit = 20) =>
  useQuery({ queryKey: ["runs", limit], queryFn: () => api.getRuns(limit) });

export const useFindings = (runId: number, opts?: { params?: Record<string, string>; enabled?: boolean }) =>
  useQuery({
    queryKey: ["findings", runId, opts?.params],
    queryFn: () => api.getFindings(runId, opts?.params),
    enabled: opts?.enabled !== undefined ? opts.enabled : !!runId,
  });

export const useStats = (runId: number) =>
  useQuery({
    queryKey: ["stats", runId],
    queryFn: () => api.getStats(runId),
    enabled: !!runId,
  });

export const useCompliance = (runId: number) =>
  useQuery({
    queryKey: ["compliance", runId],
    queryFn: () => api.getCompliance(runId),
    enabled: !!runId,
  });

export const useAutofix = (runId: number, findingId: number, enabled: boolean) =>
  useQuery({
    queryKey: ["autofix", runId, findingId],
    queryFn: () => api.getAutofix(runId, findingId),
    enabled,
  });

export const useSupplyChain = (runId: number, opts?: { riskLevel?: string; enabled?: boolean }) =>
  useQuery({
    queryKey: ["supply-chain", runId, opts?.riskLevel],
    queryFn: () => api.getSupplyChain(runId, opts?.riskLevel),
    enabled: opts?.enabled !== undefined ? opts.enabled : !!runId,
  });

export const useTrends = () =>
  useQuery({ queryKey: ["trends"], queryFn: api.getTrends });

export const useSubmitScan = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ dir, repo }: { dir: string; repo: string }) =>
      api.submitScan(dir, repo),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
};

export const usePrRisk = (runId: number) =>
  useQuery({ queryKey: ["pr-risk", runId], queryFn: () => api.getPrRisk(runId), enabled: !!runId });

export const useCostBenefit = (runId: number) =>
  useQuery({ queryKey: ["cost-benefit", runId], queryFn: () => api.getCostBenefit(runId), enabled: !!runId });

export const useReviewBottleneck = (runId: number) =>
  useQuery({ queryKey: ["review-bottleneck", runId], queryFn: () => api.getReviewBottleneck(runId), enabled: !!runId });

export const useApiKeys = () =>
  useQuery({ queryKey: ["api-keys"], queryFn: api.getApiKeys });

export const useCreateApiKey = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.createApiKey(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
};

export const useDeleteApiKey = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteApiKey(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });
};

export const useRiskMap = (runId: number, refresh = false) =>
  useQuery({ queryKey: ["risk-map", runId, refresh], queryFn: () => api.getRiskMap(runId, refresh), enabled: !!runId });

export const useRunSummary = (runId: number) =>
  useQuery({ queryKey: ["run-summary", runId], queryFn: () => api.getRunSummary(runId), enabled: !!runId });

export const useAttestation = (runId: number) =>
  useQuery({ queryKey: ["attestation", runId], queryFn: () => api.getAttestation(runId), enabled: !!runId });

// ── Vulnerabilities (Phase 1) ──────────────────────────────────────────────────

export const useVulnerability = (shortId: string | undefined) =>
  useQuery({
    queryKey: ["vuln", shortId],
    queryFn: () => api.getVulnerability(shortId!),
    enabled: !!shortId,
  });

export const useVulnFindings = (vulnId: number | undefined) =>
  useQuery({
    queryKey: ["vuln-findings", vulnId],
    queryFn: () => api.getVulnFindings(vulnId!),
    enabled: !!vulnId,
  });

export const useVulnerabilities = (params?: Parameters<typeof api.listVulnerabilities>[0]) =>
  useQuery({
    queryKey: ["vulnerabilities", params],
    queryFn: () => api.listVulnerabilities(params),
  });

export const usePatchVulnStatus = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ vulnId, status }: { vulnId: number; status: api.VulnStatus }) =>
      api.patchVulnStatus(vulnId, status),
    onSuccess: (data) => {
      qc.setQueryData(["vuln", data.short_id], data);
      qc.invalidateQueries({ queryKey: ["vulnerabilities"] });
    },
  });
};

export const usePatchVulnOwner = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ vulnId, owner }: { vulnId: number; owner: string | null }) =>
      api.patchVulnOwner(vulnId, owner),
    onSuccess: (data) => {
      qc.setQueryData(["vuln", data.short_id], data);
    },
  });
};

// ── Inbox (Phase 2) ────────────────────────────────────────────────────────────

export const useInbox = (staleDays = 7) =>
  useQuery({
    queryKey: ["inbox", staleDays],
    queryFn: () => api.getInbox(staleDays),
    refetchInterval: 60_000,
  });

export const useBulkPatch = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.bulkPatch,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["inbox"] });
      qc.invalidateQueries({ queryKey: ["vulnerabilities"] });
    },
  });
};

export const useAIDetection = () =>
  useMutation({ mutationFn: ({ target, threshold }: { target: string; threshold?: number }) => api.postAIDetection(target, threshold) });

// ── Relationships (Phase 3) ────────────────────────────────────────────────────

export const useRelated = (vulnId: number | undefined) =>
  useQuery({
    queryKey: ["related", vulnId],
    queryFn: () => api.getRelated(vulnId!),
    enabled: !!vulnId,
    staleTime: 120_000,
  });

export const useRuleStats = (ruleId: string | undefined) =>
  useQuery({
    queryKey: ["rule-stats", ruleId],
    queryFn: () => api.getRuleStats(ruleId!),
    enabled: !!ruleId,
    staleTime: 120_000,
  });

export const useSearch = (q: string) =>
  useQuery({
    queryKey: ["search", q],
    queryFn: () => api.searchObjects(q),
    enabled: q.trim().length >= 2,
    staleTime: 30_000,
  });

// ── Fleet (Phase 4) ────────────────────────────────────────────────────────────

export const useFleet = (limit = 50) =>
  useQuery({
    queryKey: ["fleet", limit],
    queryFn: () => api.getFleet(limit),
    staleTime: 60_000,
    refetchInterval: 30_000,
  });

export const useFleetCompliance = () =>
  useQuery({
    queryKey: ["fleet-compliance"],
    queryFn: api.getFleetCompliance,
    staleTime: 120_000,
  });

export const useStride = (repoName: string | null) =>
  useQuery({
    queryKey: ["stride", repoName],
    queryFn: () => api.getStride(repoName!),
    enabled: !!repoName,
    staleTime: 120_000,
  });

// ── Workbench (Phase 5) ────────────────────────────────────────────────────────

export const useWbQuery = (params: api.WbQueryParams, enabled = true) =>
  useQuery({
    queryKey: ["wb-query", params],
    queryFn: () => api.wbQuery(params),
    enabled,
    staleTime: 30_000,
  });

export const useRulePerformance = (limit = 50) =>
  useQuery({
    queryKey: ["rule-perf", limit],
    queryFn: () => api.getRulePerformance(limit),
    staleTime: 120_000,
  });

export const useAuditLog = (limit = 100, repo?: string) =>
  useQuery({
    queryKey: ["audit-log", limit, repo],
    queryFn: () => api.getAuditLog(limit, repo),
    staleTime: 60_000,
  });

export const useLabels = (params: Parameters<typeof api.getLabels>[0] = {}) =>
  useQuery({
    queryKey: ["labels", params],
    queryFn: () => api.getLabels(params),
    staleTime: 10_000,
  });

export const useSetLabel = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, gt, reasoning }: { id: number; gt: string; reasoning?: string }) =>
      api.setLabel(id, gt, reasoning),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["labels"] }),
  });
};

export const useAttackPaths = (vulnId: number | undefined, depth = 3) =>
  useQuery({
    queryKey: ["attack-paths", vulnId, depth],
    queryFn: () => api.getAttackPaths(vulnId!, depth),
    enabled: !!vulnId,
    staleTime: 120_000,
  });

// ── Trust (Phase 6) ────────────────────────────────────────────────────────────

export const useTrustPosture = (repoName: string) =>
  useQuery({
    queryKey: ["trust-posture", repoName],
    queryFn: () => api.getTrustPosture(repoName),
    enabled: !!repoName,
    staleTime: 120_000,
    retry: 1,
  });

export const useTrustAttestation = (repoName: string) =>
  useQuery({
    queryKey: ["trust-attestation", repoName],
    queryFn: () => api.getTrustAttestation(repoName),
    enabled: !!repoName,
    staleTime: 300_000,
  });

export const useTrustPublicKey = (repoName: string) =>
  useQuery({
    queryKey: ["trust-pubkey", repoName],
    queryFn: () => api.getTrustPublicKey(repoName),
    enabled: !!repoName,
    staleTime: 3_600_000,
  });
