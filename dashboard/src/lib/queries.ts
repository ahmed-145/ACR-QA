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

export const useAIDetection = () =>
  useMutation({ mutationFn: ({ target, threshold }: { target: string; threshold?: number }) => api.postAIDetection(target, threshold) });
