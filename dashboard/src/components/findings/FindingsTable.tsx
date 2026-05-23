import { useState } from "react";
import { type Finding } from "@/lib/api";
import { truncate } from "@/lib/utils";
import { Search } from "lucide-react";

interface Props {
  findings: Finding[];
  onSelect: (f: Finding) => void;
}

type SortKey = "severity" | "confidence" | "rule_id";

const SEV_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export function FindingsTable({ findings, onSelect }: Props) {
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const sortKey: SortKey = "severity";
  const sortAsc = true;

  const filtered = findings
    .filter((f) => {
      if (severityFilter !== "all" && f.severity !== severityFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          f.rule_id?.toLowerCase().includes(q) ||
          f.message?.toLowerCase().includes(q) ||
          f.file_path?.toLowerCase().includes(q)
        );
      }
      return true;
    })
    .sort((a, b) => {
      let cmp = 0;
      if (sortKey === "severity") cmp = (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9);
      else if (sortKey === "confidence") cmp = (b.confidence ?? 0) - (a.confidence ?? 0);
      else if (sortKey === "rule_id") cmp = (a.rule_id ?? "").localeCompare(b.rule_id ?? "");
      return sortAsc ? cmp : -cmp;
    });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Controls */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 180, maxWidth: 320 }}>
          <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--fg-5)", pointerEvents: "none" }} aria-hidden />
          <input
            className="inp"
            style={{ paddingLeft: 32 }}
            placeholder="Search rule, file, message…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filter-row" style={{ margin: 0 }}>
          {["all", "high", "medium", "low"].map((s) => (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={`pill${severityFilter === s ? " on" : ""}`}
            >
              {s === "all" ? "ALL" : s.toUpperCase()}
            </button>
          ))}
        </div>
        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-5)", marginLeft: "auto" }}>
          {filtered.length} / {findings.length}
        </span>
      </div>

      {/* Findings list */}
      <div className="findings">
        {filtered.length === 0 ? (
          <div className="empty">No findings match your filters</div>
        ) : (
          filtered.map((f) => {
            const sevCls = f.severity === "high" || f.severity === "critical" ? "high" : f.severity === "medium" ? "med" : "low";
            const conf = Math.round((f.confidence ?? 0) * 100);
            return (
              <div
                key={f.id}
                className={`finding ${sevCls}`}
                onClick={() => onSelect(f)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && onSelect(f)}
              >
                <span className={`sev ${sevCls}`}>{f.severity.toUpperCase()}</span>
                <div className="finding-body">
                  <div className="finding-msg">{truncate(f.message ?? "", 90)}</div>
                  <div className="finding-meta">
                    <span className="rule">{f.rule_id}</span>
                    <span className="sep">·</span>
                    <span className="file">{truncate(f.file_path ?? "", 40)}</span>
                    {f.line_number && (
                      <>
                        <span className="sep">:</span>
                        <span className="line">{f.line_number}</span>
                      </>
                    )}
                  </div>
                </div>
                {conf > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
                    <span className={`conf ${conf >= 70 ? "hi" : conf >= 40 ? "md" : "lo"}`}>{conf}%</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
