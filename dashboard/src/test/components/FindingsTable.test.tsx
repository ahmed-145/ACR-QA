import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FindingsTable } from "@/components/findings/FindingsTable";
import type { Finding } from "@/lib/api";

const makeF = (overrides: Partial<Finding> = {}): Finding => ({
  id: 1,
  rule_id: "S001",
  severity: "HIGH",
  category: "injection",
  file_path: "src/app.py",
  line_number: 42,
  line_start: 42,
  message: "SQL injection detected",
  explanation_text: "Use parameterized queries",
  model_name: "gpt-4",
  confidence: 0.9,
  tool: "semgrep",
  taint_source: null,
  taint_path: null,
  taint_confidence: null,
  triage_verdict: null,
  triage_reasoning: null,
  triage_confidence_delta: null,
  ground_truth: null,
  exploit_tier: null,
  exploit_proof: null,
  exploit_evidence: null,
  exploit_duration_seconds: null,
  ...overrides,
});

describe("FindingsTable", () => {
  it("renders finding rule_id", () => {
    render(<FindingsTable findings={[makeF()]} onSelect={vi.fn()} />);
    expect(screen.getByText("S001")).toBeInTheDocument();
  });

  it("renders file path", () => {
    render(<FindingsTable findings={[makeF()]} onSelect={vi.fn()} />);
    expect(screen.getByText(/src\/app\.py/)).toBeInTheDocument();
  });

  it("renders severity badge in table", () => {
    render(<FindingsTable findings={[makeF()]} onSelect={vi.fn()} />);
    expect(screen.getAllByText("HIGH").length).toBeGreaterThanOrEqual(1);
  });

  it("shows empty state when no findings", () => {
    render(<FindingsTable findings={[]} onSelect={vi.fn()} />);
    expect(screen.getByText(/no findings/i)).toBeInTheDocument();
  });

  it("filters findings by search input", () => {
    const findings = [makeF({ rule_id: "SQL001" }), makeF({ id: 2, rule_id: "XSS002" })];
    render(<FindingsTable findings={findings} onSelect={vi.fn()} />);
    const input = screen.getByPlaceholderText(/search/i);
    fireEvent.change(input, { target: { value: "XSS" } });
    expect(screen.queryByText("SQL001")).not.toBeInTheDocument();
    expect(screen.getByText("XSS002")).toBeInTheDocument();
  });

  it("calls onSelect when row clicked", () => {
    const onSelect = vi.fn();
    render(<FindingsTable findings={[makeF()]} onSelect={onSelect} />);
    fireEvent.click(screen.getByText("S001").closest("[role=button]")!);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
  });
});
