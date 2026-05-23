import { useState, useMemo, useRef, useCallback, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useRuns } from "@/lib/queries";
import { getFindings } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { Search, Filter, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { useUrlStateMulti } from "@/lib/useUrlState";
import { useShortcuts } from "@/lib/useShortcuts";
import { SidePanel } from "@/components/ui/SidePanel";
import { SkeletonRow } from "@/components/ui/SkeletonRow";
import { KbdHint } from "@/components/ui/KbdHint";
import type { Finding } from "@/lib/api";

const SEV_ORDER: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };
const PAGE_SIZE = 50;

interface FindingWithRun extends Finding {
  run_id: number;
  repo_name: string;
}

function useAllFindings(runIds: { id: number; repo_name: string }[]) {
  return useQuery({
    queryKey: ["all-findings", runIds.map((r) => r.id).join(",")],
    queryFn: async (): Promise<FindingWithRun[]> => {
      const results = await Promise.allSettled(
        runIds.map((r) =>
          getFindings(r.id).then((d) =>
            d.findings.map((f) => ({ ...f, run_id: r.id, repo_name: r.repo_name }))
          )
        )
      );
      return results
        .filter((r): r is PromiseFulfilledResult<FindingWithRun[]> => r.status === "fulfilled")
        .flatMap((r) => r.value);
    },
    enabled: runIds.length > 0,
    staleTime: 60_000,
  });
}

function FindingDetail({ finding }: { finding: FindingWithRun }) {
  const sev = finding.severity.toUpperCase();
  const sevCls = sev === "HIGH" ? "high" : sev === "MEDIUM" ? "med" : "low";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="d-chips">
        <span className={`sev ${sevCls}`}>{sev}</span>
        <span className="d-rule-id">{finding.rule_id}</span>
        <span className="d-tool">{finding.repo_name}</span>
      </div>
      <div style={{ fontSize: 15, fontWeight: 600, color: "var(--fg)", lineHeight: 1.35 }}>{finding.message}</div>
      <div className="d-path" style={{ fontSize: 12 }}>
        <span style={{ color: "var(--fg-3)" }}>{finding.file_path}</span>
        {finding.line_number && <span className="line">:{finding.line_number}</span>}
      </div>
      {finding.category && (
        <div style={{ fontSize: 12, color: "var(--fg-4)" }}>Category: <span style={{ color: "var(--fg-2)" }}>{finding.category}</span></div>
      )}
      {(finding as unknown as { evidence?: { snippet?: string } }).evidence?.snippet && (
        <div className="evidence-block" style={{ marginTop: 4 }}>
          <div className="evidence-header">
            <span>EVIDENCE</span>
            <span className="hl-file">{finding.file_path}{finding.line_number ? `:${finding.line_number}` : ""}</span>
          </div>
          <pre className="evidence-code">
            {(finding as unknown as { evidence?: { snippet?: string } }).evidence?.snippet}
          </pre>
        </div>
      )}
      <Link
        to={`/runs/${finding.run_id}`}
        className="btn-ghost"
        style={{ height: 30, fontSize: 12, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6, alignSelf: "flex-start", marginTop: 4 }}
      >
        <ExternalLink size={12} aria-hidden /> View Full Run #{finding.run_id}
      </Link>
    </div>
  );
}

export function FindingsPage() {
  const { data: runsData } = useRuns(20);
  const runs = runsData?.runs ?? [];
  const completedRuns = runs.filter((r) => r.status === "completed").slice(0, 10);
  const navigate = useNavigate();

  const [filters, setFilters] = useUrlStateMulti({ sev: "ALL", cat: "ALL", run: "ALL", q: "", page: "0" });
  const [panelFinding, setPanelFinding] = useState<FindingWithRun | null>(null);
  const [cursorIdx, setCursorIdx] = useState(0);
  const tableRef = useRef<HTMLDivElement>(null);

  const search = filters.q;
  const sevFilter = filters.sev;
  const catFilter = filters.cat;
  const runFilter = filters.run;
  const page = parseInt(filters.page, 10) || 0;

  const setPage = useCallback((p: number) => setFilters({ page: String(p) }), [setFilters]);

  const { data: allFindings = [], isLoading } = useAllFindings(
    completedRuns.map((r) => ({ id: r.id, repo_name: r.repo_name }))
  );

  const categories = useMemo(() => {
    const cats = new Set(allFindings.map((f) => f.category ?? "unknown"));
    return ["ALL", ...Array.from(cats).sort()];
  }, [allFindings]);

  const filtered = useMemo(() => {
    return allFindings
      .filter((f) => {
        if (sevFilter !== "ALL" && f.severity.toUpperCase() !== sevFilter) return false;
        if (catFilter !== "ALL" && (f.category ?? "unknown") !== catFilter) return false;
        if (runFilter !== "ALL" && String(f.run_id) !== runFilter) return false;
        if (search) {
          const q = search.toLowerCase();
          return (
            f.rule_id.toLowerCase().includes(q) ||
            f.file_path.toLowerCase().includes(q) ||
            f.message.toLowerCase().includes(q)
          );
        }
        return true;
      })
      .sort((a, b) => (SEV_ORDER[a.severity.toUpperCase()] ?? 3) - (SEV_ORDER[b.severity.toUpperCase()] ?? 3));
  }, [allFindings, sevFilter, catFilter, runFilter, search]);

  const paginated = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  useEffect(() => { setCursorIdx(0); }, [page, sevFilter, catFilter, runFilter, search]);

  useShortcuts([
    { key: "j", handler: () => setCursorIdx((i) => Math.min(i + 1, paginated.length - 1)) },
    { key: "k", handler: () => setCursorIdx((i) => Math.max(i - 1, 0)) },
    { key: "o", handler: () => { if (paginated[cursorIdx]) setPanelFinding(paginated[cursorIdx]); } },
    { key: "x", handler: () => setPanelFinding(null) },
    { key: "Enter", handler: () => { if (paginated[cursorIdx]) navigate(`/runs/${paginated[cursorIdx].run_id}`); } },
    { key: "ArrowRight", handler: () => { if (page < totalPages - 1) setPage(page + 1); }, preventDefault: true },
    { key: "ArrowLeft",  handler: () => { if (page > 0) setPage(page - 1); }, preventDefault: true },
  ]);

  function sevRowClass(sev: string) {
    if (sev === "HIGH")   return "finding-row-high";
    if (sev === "MEDIUM") return "finding-row-med";
    return "finding-row-low";
  }

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">All Findings</span>
        </div>
        <span className="grow" />
        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>
          {filtered.length} findings · {completedRuns.length} runs
        </span>
        <KbdHint shortcut={["j", "k"]} label="navigate" />
        <KbdHint shortcut="o" label="preview" />
      </div>

      <h1 className="title" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0,0,0,0)", whiteSpace: "nowrap" }}>All Findings</h1>

      {/* Sticky filter bar */}
      <div className="sticky-filters">
        <div style={{ position: "relative", flex: "1 1 220px", minWidth: 160 }}>
          <Search size={12} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: "var(--fg-5)", pointerEvents: "none" }} aria-hidden />
          <input
            className="inp inp-sm"
            style={{ paddingLeft: 28, width: "100%" }}
            placeholder="Search rules, files, messages…"
            value={search}
            onChange={(e) => { setFilters({ q: e.target.value, page: "0" }); }}
            aria-label="Search findings"
          />
        </div>

        <div style={{ display: "flex", gap: 4 }}>
          {["ALL", "HIGH", "MEDIUM", "LOW"].map((s) => (
            <button
              key={s}
              className={`pill${sevFilter === s ? " on" : ""}`}
              onClick={() => setFilters({ sev: s, page: "0" })}
              aria-pressed={sevFilter === s}
            >{s}</button>
          ))}
        </div>

        <div style={{ position: "relative" }}>
          <Filter size={11} style={{ position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)", color: "var(--fg-5)", pointerEvents: "none" }} aria-hidden />
          <select
            value={catFilter}
            onChange={(e) => setFilters({ cat: e.target.value, page: "0" })}
            style={{
              appearance: "none", background: "var(--bg-3)", border: "1px solid var(--border-2)",
              color: "var(--fg-2)", borderRadius: 7, padding: "5px 10px 5px 24px",
              fontSize: 12, fontFamily: "var(--font)", cursor: "pointer",
            }}
            aria-label="Filter by category"
          >
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <select
          value={runFilter}
          onChange={(e) => setFilters({ run: e.target.value, page: "0" })}
          style={{
            appearance: "none", background: "var(--bg-3)", border: "1px solid var(--border-2)",
            color: "var(--fg-2)", borderRadius: 7, padding: "5px 10px",
            fontSize: 12, fontFamily: "var(--font)", cursor: "pointer",
          }}
          aria-label="Filter by run"
        >
          <option value="ALL">All repos</option>
          {completedRuns.map((r) => (
            <option key={r.id} value={String(r.id)}>{r.repo_name} #{r.id}</option>
          ))}
        </select>
      </div>

      <div className="page-pad" style={{ paddingTop: 20 }}>
        <div className="panel" style={{ padding: 0, overflow: "hidden" }} ref={tableRef}>
          {isLoading ? (
            <>
              {Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={6} />)}
            </>
          ) : paginated.length === 0 ? (
            <div style={{ padding: 48, textAlign: "center", color: "var(--fg-5)", fontSize: 13 }}>
              No findings match your filters.
            </div>
          ) : (
            <>
              <div style={{
                display: "grid", gridTemplateColumns: "72px 90px 130px 1fr 110px 70px",
                gap: 0, padding: "7px 16px",
                borderBottom: "1px solid var(--border)",
                background: "var(--bg-3)",
                position: "sticky", top: "108px", zIndex: 5,
              }}>
                {["SEV", "RULE", "REPO", "FILE / MESSAGE", "CATEGORY", "RUN"].map((h) => (
                  <div key={h} style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)", padding: "0 8px", textTransform: "uppercase", letterSpacing: "0.08em" }}>{h}</div>
                ))}
              </div>

              {paginated.map((f, idx) => {
                const sev = f.severity.toUpperCase();
                const sevCls = sev === "HIGH" ? "high" : sev === "MEDIUM" ? "med" : "low";
                const isActive = idx === cursorIdx;
                return (
                  <div
                    key={`${f.run_id}-${f.id}`}
                    className={sevRowClass(sev)}
                    style={{
                      display: "grid", gridTemplateColumns: "72px 90px 130px 1fr 110px 70px",
                      gap: 0, padding: "9px 16px",
                      borderBottom: "1px solid var(--border)",
                      cursor: "pointer",
                      outline: isActive ? "1px solid rgba(167,139,250,0.4)" : "none",
                      outlineOffset: -1,
                    }}
                    onClick={() => { setCursorIdx(idx); setPanelFinding(f); }}
                    onDoubleClick={() => navigate(`/runs/${f.run_id}`)}
                    role="row"
                    aria-selected={isActive}
                    tabIndex={isActive ? 0 : -1}
                  >
                    <div style={{ padding: "0 8px" }}><span className={`sev ${sevCls}`}>{sev}</span></div>
                    <div style={{ padding: "0 8px", fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--fg-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.rule_id}</div>
                    <div style={{ padding: "0 8px", fontSize: 11.5, color: "var(--fg-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.repo_name}</div>
                    <div style={{ padding: "0 8px", overflow: "hidden" }}>
                      <div style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--fg-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {f.file_path}{f.line_number ? `:${f.line_number}` : ""}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--fg-4)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: 1 }}>{f.message}</div>
                    </div>
                    <div style={{ padding: "0 8px", fontSize: 11, color: "var(--fg-4)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.category ?? "—"}</div>
                    <div style={{ padding: "0 8px" }}>
                      <span className="id-pill">#{f.run_id}</span>
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>

        {totalPages > 1 && (
          <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 16, alignItems: "center" }}>
            <button className="btn-ghost" style={{ height: 30, fontSize: 12 }} disabled={page === 0} onClick={() => setPage(page - 1)}>
              <ChevronLeft size={13} aria-hidden /> Prev
            </button>
            <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-4)" }}>
              {page + 1} / {totalPages}
            </span>
            <button className="btn-ghost" style={{ height: 30, fontSize: 12 }} disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>
              Next <ChevronRight size={13} aria-hidden />
            </button>
          </div>
        )}
      </div>

      <SidePanel
        open={panelFinding !== null}
        onClose={() => setPanelFinding(null)}
        title={panelFinding ? `${panelFinding.rule_id} — ${panelFinding.severity.toUpperCase()}` : ""}
        width={460}
      >
        {panelFinding && <FindingDetail finding={panelFinding} />}
      </SidePanel>
    </>
  );
}
