import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { FindingHistory } from "@/components/findings/FindingHistory";

function jsonResp(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const sample = {
  finding_id: 7,
  file_path: "app.py",
  line_number: 5,
  rule_id: "SEC-001",
  first_seen_commit: {
    sha: "abc1234deadbeef",
    date: "2025-12-01T00:00:00Z",
    author: "Ahmed",
    subject: "Initial: introduce shell exec helper",
  },
  first_seen_author: "Ahmed",
  first_seen_date: "2025-12-01T00:00:00Z",
  commits_touching: [
    { sha: "fffeeeeddd00000", date: "2026-01-02T00:00:00Z", author: "B", subject: "Refactor pass" },
    { sha: "abc1234deadbeef", date: "2025-12-01T00:00:00Z", author: "Ahmed", subject: "Initial: introduce shell exec helper" },
  ],
  regression_count: 0,
  near_fix_commits: [
    { sha: "fffeeeeddd00000", date: "2026-01-02T00:00:00Z", author: "B", subject: "Refactor pass" },
  ],
  bounded_by_max_commits: true,
};

describe("FindingHistory", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading then history", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResp(sample));
    render(<FindingHistory findingId={7} />);
    expect(screen.getByTestId("history-loading")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("history")).toBeInTheDocument());
  });

  it("renders first-seen author and regression count", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResp(sample));
    render(<FindingHistory findingId={7} />);
    await waitFor(() => expect(screen.getByTestId("history")).toBeInTheDocument());
    expect(screen.getByTestId("first-seen-commit").textContent).toContain("Ahmed");
    expect(screen.getByTestId("regression-count").textContent).toBe("0");
    expect(screen.getByTestId("commits-touching-count").textContent).toBe("2");
  });

  it("marks first-seen and near-fix commits with data attributes", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResp(sample));
    render(<FindingHistory findingId={7} />);
    await waitFor(() => expect(screen.getByTestId("commits-strip")).toBeInTheDocument());
    const firstSeen = screen.getByTestId(`commit-${sample.first_seen_commit.sha}`);
    expect(firstSeen.getAttribute("data-first-seen")).toBe("1");
    const nearFix = screen.getByTestId(`commit-${sample.near_fix_commits[0].sha}`);
    expect(nearFix.getAttribute("data-near-fix")).toBe("1");
  });

  it("renders near-fix note when there are near-fix commits", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResp(sample));
    render(<FindingHistory findingId={7} />);
    await waitFor(() => expect(screen.getByTestId("near-fix-note")).toBeInTheDocument());
  });

  it("renders empty state when no git history", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResp({
        ...sample,
        first_seen_commit: null,
        first_seen_author: null,
        first_seen_date: null,
        commits_touching: [],
        near_fix_commits: [],
      }),
    );
    render(<FindingHistory findingId={7} />);
    await waitFor(() => expect(screen.getByTestId("history-empty")).toBeInTheDocument());
  });

  it("renders error on fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResp({}, 500));
    render(<FindingHistory findingId={7} />);
    await waitFor(() => expect(screen.getByTestId("history-error")).toBeInTheDocument());
  });

  it("shortens commit SHA to 7 chars", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(jsonResp(sample));
    render(<FindingHistory findingId={7} />);
    await waitFor(() => expect(screen.getByTestId("history")).toBeInTheDocument());
    const firstSeen = screen.getByTestId(`commit-${sample.first_seen_commit.sha}`);
    expect(firstSeen.textContent).toContain(sample.first_seen_commit.sha.slice(0, 7));
  });
});
