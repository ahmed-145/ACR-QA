import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ComplianceData } from "@/lib/api";

const getCompliance = vi.fn();
vi.mock("@/lib/api", () => ({
  getCompliance: (...args: unknown[]) => getCompliance(...args),
}));

import { OwaspHeatmap } from "@/components/compliance/OwaspHeatmap";

function makeCompliance(overrides: Partial<Record<string, { name: string; status: "PASS" | "FAIL"; finding_count: number; cwe_ids: string[] }>>): ComplianceData {
  const base: ComplianceData["owasp_results"] = {};
  const names: Record<string, string> = {
    A01: "Broken Access Control", A02: "Cryptographic Failures", A03: "Injection",
    A04: "Insecure Design", A05: "Security Misconfiguration", A06: "Vulnerable Components",
    A07: "Auth Failures", A08: "Data Integrity", A09: "Logging Failures", A10: "SSRF",
  };
  for (const id of Object.keys(names)) {
    base[id] = { name: names[id], status: "PASS", finding_count: 0, cwe_ids: [], ...overrides[id] };
  }
  return {
    success: true, run_id: 1, version: "5", total_findings: 0, security_findings: 0,
    owasp_results: base, unmapped_security_findings: [],
  };
}

function renderHeatmap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <OwaspHeatmap runId={1} />
    </QueryClientProvider>,
  );
}

describe("OwaspHeatmap — reads real owasp_results shape", () => {
  beforeEach(() => getCompliance.mockReset());

  it("renders the real finding_count from owasp_results (not the old .count field)", async () => {
    getCompliance.mockResolvedValue(
      makeCompliance({ A03: { name: "Injection", status: "FAIL", finding_count: 7, cwe_ids: ["CWE-89"] } }),
    );
    renderHeatmap();

    await waitFor(() => expect(screen.getByText("OWASP Top 10 Coverage")).toBeInTheDocument());
    // The Injection cell must show the real count 7.
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("computes compliance score as passedCategories * 10", async () => {
    // 2 categories FAIL → 8 PASS → score 80%.
    getCompliance.mockResolvedValue(
      makeCompliance({
        A01: { name: "Broken Access Control", status: "FAIL", finding_count: 1, cwe_ids: [] },
        A03: { name: "Injection", status: "FAIL", finding_count: 2, cwe_ids: [] },
      }),
    );
    renderHeatmap();

    await waitFor(() => expect(screen.getByText(/Score: 80%/)).toBeInTheDocument());
  });

  it("shows 100% score when all categories pass", async () => {
    getCompliance.mockResolvedValue(makeCompliance({}));
    renderHeatmap();
    await waitFor(() => expect(screen.getByText(/Score: 100%/)).toBeInTheDocument());
  });
});
