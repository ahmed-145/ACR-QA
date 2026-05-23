import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { authHeader } from "@/lib/auth";
import { Search } from "lucide-react";

interface Rule {
  canonical_id: string;
  category: string;
  severity: string;
  tool_ids: string[];
}

function useRules() {
  return useQuery({
    queryKey: ["rules"],
    queryFn: async (): Promise<Rule[]> => {
      const res = await fetch("/v1/rules", { headers: authHeader() });
      if (!res.ok) throw new Error("Failed to load rules");
      const d = await res.json();
      return d.rules;
    },
    staleTime: 5 * 60_000,
  });
}

const SEV_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

const CATEGORIES = [
  "ALL", "security", "hardcode", "import", "var", "dead", "naming",
  "style", "pattern", "type", "complexity", "dup", "except", "async",
  "solid", "iac", "other",
];

export function RulesPage() {
  const { data: rules = [], isLoading } = useRules();
  const [search, setSearch] = useState("");
  const [sevFilter, setSevFilter] = useState("ALL");
  const [catFilter, setCatFilter] = useState("ALL");

  const filtered = useMemo(() => {
    return rules
      .filter((r) => {
        if (sevFilter !== "ALL" && r.severity !== sevFilter.toLowerCase()) return false;
        if (catFilter !== "ALL" && r.category !== catFilter) return false;
        if (search) {
          const q = search.toLowerCase();
          return (
            r.canonical_id.toLowerCase().includes(q) ||
            r.category.toLowerCase().includes(q) ||
            r.tool_ids.some((t) => t.toLowerCase().includes(q))
          );
        }
        return true;
      })
      .sort((a, b) => (SEV_ORDER[a.severity] ?? 3) - (SEV_ORDER[b.severity] ?? 3) || a.canonical_id.localeCompare(b.canonical_id));
  }, [rules, sevFilter, catFilter, search]);

  const catCounts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const r of rules) m[r.category] = (m[r.category] ?? 0) + 1;
    return m;
  }, [rules]);

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Rules Browser</span>
        </div>
        <span className="grow" />
        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>
          {filtered.length} / {rules.length} rules
        </span>
      </div>

      <div className="page-pad">
        <h1 className="title">Rules Browser</h1>
        <p className="subtitle">All {rules.length} canonical detection rules — searchable by severity, category, or tool ID</p>

        {/* Stats */}
        <div className="stats" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 20 }}>
          {[
            { label: "Total Rules", value: rules.length, cls: "" },
            { label: "HIGH Severity", value: rules.filter((r) => r.severity === "high").length, cls: " danger" },
            { label: "MEDIUM Severity", value: rules.filter((r) => r.severity === "medium").length, cls: "" },
            { label: "LOW Severity", value: rules.filter((r) => r.severity === "low").length, cls: "" },
          ].map(({ label, value, cls }) => (
            <div key={label} className="stat">
              <div className="lbl">{label}</div>
              <div className={`num${cls}`}>{value}</div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ position: "relative", flex: "1 1 200px", minWidth: 160 }}>
            <Search size={12} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: "var(--fg-5)", pointerEvents: "none" }} aria-hidden />
            <input
              className="inp"
              style={{ paddingLeft: 28 }}
              placeholder="Search canonical ID, category, tool ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            {["ALL", "HIGH", "MEDIUM", "LOW"].map((s) => (
              <button key={s} className={`pill${sevFilter === s ? " on" : ""}`} onClick={() => setSevFilter(s)}>{s}</button>
            ))}
          </div>
          <select
            value={catFilter}
            onChange={(e) => setCatFilter(e.target.value)}
            style={{
              appearance: "none", background: "var(--bg-3)", border: "1px solid var(--border-2)",
              color: "var(--fg-2)", borderRadius: 7, padding: "6px 10px",
              fontSize: 12, fontFamily: "var(--font)", cursor: "pointer",
            }}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c === "ALL" ? "All categories" : `${c} (${catCounts[c] ?? 0})`}</option>
            ))}
          </select>
        </div>

        {/* Rules grid */}
        {isLoading ? (
          <div className="empty"><span className="spinner" /> Loading rules…</div>
        ) : (
          <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
            {/* Header */}
            <div style={{
              display: "grid", gridTemplateColumns: "180px 80px 120px 1fr",
              padding: "8px 16px", borderBottom: "1px solid var(--border)",
              background: "var(--bg-3)",
            }}>
              {["Canonical ID", "Severity", "Category", "Covers (tool-native IDs)"].map((h) => (
                <div key={h} style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)", textTransform: "uppercase", letterSpacing: "0.08em" }}>{h}</div>
              ))}
            </div>

            {filtered.length === 0 ? (
              <div style={{ padding: 32, textAlign: "center", color: "var(--fg-5)", fontSize: 13 }}>
                No rules match your filters.
              </div>
            ) : (
              filtered.map((rule) => {
                const sevCls = rule.severity === "high" ? "high" : rule.severity === "medium" ? "med" : "low";
                return (
                  <div key={rule.canonical_id} style={{
                    display: "grid", gridTemplateColumns: "180px 80px 120px 1fr",
                    padding: "9px 16px", borderBottom: "1px solid var(--border)",
                    alignItems: "center",
                  }}>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 12, fontWeight: 600, color: "var(--fg)" }}>
                      {rule.canonical_id}
                    </div>
                    <div><span className={`sev ${sevCls}`}>{rule.severity.toUpperCase()}</span></div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>{rule.category}</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {rule.tool_ids.slice(0, 8).map((tid) => (
                        <span key={tid} style={{
                          fontFamily: "var(--mono)", fontSize: 10, padding: "1px 6px",
                          borderRadius: 4, background: "rgba(255,255,255,0.04)",
                          border: "1px solid var(--border)", color: "var(--fg-4)",
                        }}>{tid}</span>
                      ))}
                      {rule.tool_ids.length > 8 && (
                        <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)" }}>
                          +{rule.tool_ids.length - 8}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </>
  );
}
