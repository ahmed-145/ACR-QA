import { useState, useRef, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  useWbQuery, useRulePerformance, useAuditLog,
  useLabels, useSetLabel, useAttackPaths, useRuns,
} from "@/lib/queries";
import * as api from "@/lib/api";
import { CountUp } from "@/components/ui/CountUp";
import { StatusBar } from "@/components/ui/StatusBar";
import {
  Terminal, BarChart2, Clock, Tag, Edit3, Globe,
  MessageSquare, Download, ChevronRight,
  Play, Search, Zap, CheckCircle, XCircle,
  AlertTriangle, Filter, BookmarkPlus,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

const TABS = [
  { id: "query",      label: "Query",        icon: <Terminal size={13} aria-hidden /> },
  { id: "rules",      label: "Rule Perf",    icon: <BarChart2 size={13} aria-hidden /> },
  { id: "audit",      label: "Audit Log",    icon: <Clock size={13} aria-hidden /> },
  { id: "labelling",  label: "Labelling",    icon: <Tag size={13} aria-hidden /> },
  { id: "editor",     label: "Rule Editor",  icon: <Edit3 size={13} aria-hidden /> },
  { id: "api",        label: "API Console",  icon: <Globe size={13} aria-hidden /> },
  { id: "chat",       label: "Triage Chat",  icon: <MessageSquare size={13} aria-hidden /> },
] as const;
type TabId = typeof TABS[number]["id"];

const SEV_COLOR: Record<string, string> = {
  high: "var(--sev-high)", medium: "var(--sev-medium)", low: "var(--sev-low)",
};

// ── Saved queries ──────────────────────────────────────────────────────────────

const LS_KEY = "acrqa:wb:saved_queries";
type SavedQuery = { name: string; params: api.WbQueryParams; nl?: string };

function loadSaved(): SavedQuery[] {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); } catch { return []; }
}
function persist(qs: SavedQuery[]) { localStorage.setItem(LS_KEY, JSON.stringify(qs)); }

// ── Notebook cells ─────────────────────────────────────────────────────────────

type Cell = { id: number; params: api.WbQueryParams; nl: string; view: "table" | "chart" };

let _cellId = 0;
function newCell(params: api.WbQueryParams = {}, nl = ""): Cell {
  return { id: ++_cellId, params, nl, view: "table" };
}

// ── Query tab ─────────────────────────────────────────────────────────────────

function QueryCell({ cell, onRemove }: { cell: Cell; onRemove: () => void }) {
  const [view, setView] = useState<"table" | "chart">(cell.view);
  const { data, isLoading } = useWbQuery(cell.params, Object.keys(cell.params).length > 0 || !!cell.nl);
  const navigate = useNavigate();
  const results = data?.results ?? [];

  return (
    <div className="wb-cell">
      <div className="wb-cell-head">
        <span className="wb-cell-label">
          {cell.nl ? <><Zap size={11} aria-hidden style={{ color: "var(--accent-2)" }} /> {cell.nl}</> : (
            Object.entries(cell.params)
              .filter(([, v]) => v != null && v !== "")
              .map(([k, v]) => `${k}:${v}`)
              .join("  ·  ") || "all vulnerabilities"
          )}
        </span>
        <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
          <button className={`wb-view-btn${view === "table" ? " on" : ""}`} onClick={() => setView("table")} aria-label="Table view">
            <Filter size={11} aria-hidden />
          </button>
          <button className={`wb-view-btn${view === "chart" ? " on" : ""}`} onClick={() => setView("chart")} aria-label="Chart view">
            <BarChart2 size={11} aria-hidden />
          </button>
          <button className="wb-view-btn danger" onClick={onRemove} aria-label="Remove cell">×</button>
        </div>
      </div>

      {isLoading ? (
        <div className="wb-cell-loading"><span className="spinner" style={{ width: 14, height: 14 }} aria-label="Loading" /></div>
      ) : view === "table" ? (
        <div className="wb-results-wrap">
          <div className="wb-results-meta">{data?.total ?? 0} results</div>
          <table className="wb-table" role="table">
            <thead>
              <tr>
                <th>ID</th><th>Rule</th><th>Sev</th><th>Status</th><th>File</th><th>Owner</th><th>Findings</th>
              </tr>
            </thead>
            <tbody>
              {results.length === 0 ? (
                <tr><td colSpan={7} style={{ textAlign: "center", color: "var(--fg-5)", padding: "16px 0" }}>No results</td></tr>
              ) : results.map((r) => (
                <tr key={r.id} className="wb-row" onClick={() => navigate(`/vuln/${r.short_id}`)} style={{ cursor: "pointer" }}>
                  <td><span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>{r.short_id}</span></td>
                  <td><span style={{ fontFamily: "var(--mono)", fontSize: 11.5 }}>{r.canonical_rule_id}</span></td>
                  <td><span className={`sev ${r.severity === "high" ? "high" : r.severity === "medium" ? "med" : "low"}`}>{r.severity.toUpperCase()}</span></td>
                  <td><span className={`vuln-status ${r.status}`}>{r.status}</span></td>
                  <td><span style={{ fontSize: 11, color: "var(--fg-4)", fontFamily: "var(--mono)" }}>{r.file_path.split("/").slice(-2).join("/")}</span></td>
                  <td><span style={{ fontSize: 11, color: "var(--fg-4)" }}>{r.owner ?? "—"}</span></td>
                  <td><span style={{ fontSize: 11.5, fontFamily: "var(--mono)", color: "var(--fg-3)" }}>{r.finding_count}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        // Simple bar chart by severity
        <div style={{ padding: "12px 0" }}>
          {(["high", "medium", "low"] as const).map((sev) => {
            const count = results.filter((r) => r.severity === sev).length;
            const pct = results.length > 0 ? (count / results.length) * 100 : 0;
            return (
              <div key={sev} className="risk-bar-item" style={{ marginBottom: 6 }}>
                <div className="risk-bar-label-row">
                  <span style={{ fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700, color: SEV_COLOR[sev] }}>{sev.toUpperCase()}</span>
                  <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>{count}</span>
                </div>
                <div className="risk-bar-track">
                  <div className="risk-bar-fill" style={{ width: `${pct}%`, background: SEV_COLOR[sev], opacity: 0.7 }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Attack Path viewer ────────────────────────────────────────────────────────

function AttackPath({ vulnId }: { vulnId: number }) {
  const navigate = useNavigate();
  const { data, isLoading } = useAttackPaths(vulnId, 3);

  if (isLoading) return <div className="wb-cell-loading"><span className="spinner" style={{ width: 14, height: 14 }} /></div>;
  if (!data || data.node_count <= 1) return <div style={{ color: "var(--fg-5)", fontSize: 12, padding: "8px 0" }}>No taint chain found.</div>;

  // Group by hop
  const byHop = data.nodes.reduce((acc, n) => {
    if (!acc[n.hop]) acc[n.hop] = [];
    acc[n.hop].push(n);
    return acc;
  }, {} as Record<number, api.AttackPathNode[]>);

  return (
    <div className="attack-path">
      {Object.entries(byHop).map(([hop, nodes], i) => (
        <div key={hop} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
          {i > 0 && <div className="attack-path-arrow"><ChevronRight size={14} aria-hidden /></div>}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {nodes.map((n) => (
              <div key={n.id} className="attack-path-node"
                   style={{ borderColor: SEV_COLOR[n.severity] }}
                   onClick={() => navigate(`/vuln/${n.short_id}`)}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: SEV_COLOR[n.severity] }}>{n.short_id}</span>
                <span style={{ fontSize: 11, color: "var(--fg-3)", marginLeft: 6 }}>{n.rule}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
      <div style={{ marginTop: 8, fontSize: 11, color: "var(--fg-5)", fontFamily: "var(--mono)" }}>
        {data.node_count} nodes · {data.edge_count} taint edges · depth {data.depth}
      </div>
    </div>
  );
}

// ── Labelling tab ─────────────────────────────────────────────────────────────

const GT_LABELS = [
  { key: "TP", label: "True Positive",  color: "var(--sev-low)", icon: <CheckCircle size={11} aria-hidden /> },
  { key: "FP", label: "False Positive", color: "var(--sev-high)", icon: <XCircle size={11} aria-hidden /> },
  { key: "TN", label: "True Negative",  color: "var(--fg-4)", icon: <CheckCircle size={11} aria-hidden /> },
  { key: "FN", label: "False Negative", color: "var(--sev-medium)", icon: <AlertTriangle size={11} aria-hidden /> },
];

function LabellingTab() {
  const [unlabelledOnly, setUnlabelledOnly] = useState(true);
  const [reasoning, setReasoning] = useState<Record<number, string>>({});
  const { data, isLoading } = useLabels({ unlabelled_only: unlabelledOnly, limit: 50 });
  const { mutate: setLabel, isPending } = useSetLabel();

  const findings = data?.findings ?? [];
  const labelled = findings.filter((f) => f.ground_truth != null).length;
  const progress = findings.length > 0 ? Math.round((labelled / findings.length) * 100) : 0;

  return (
    <div className="wb-tab-body">
      {/* Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
        <Tag size={14} aria-hidden style={{ color: "var(--fg-4)" }} />
        <span style={{ fontSize: 13, color: "var(--fg-2)", fontWeight: 600 }}>
          Ground-Truth Labelling
        </span>
        <span style={{ fontSize: 11.5, color: "var(--fg-5)", marginLeft: 4 }}>
          Label findings TP/FP/TN/FN → export .jsonl for S5 forecasting model
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--fg-4)", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={unlabelledOnly}
              onChange={(e) => setUnlabelledOnly(e.target.checked)}
              style={{ accentColor: "var(--accent-2)" }}
            />
            Unlabelled only
          </label>
          <a
            href="/v1/workbench/labels/export"
            className="btn-ghost"
            style={{ display: "flex", alignItems: "center", gap: 6, height: 30, textDecoration: "none", fontSize: 12 }}
            download="acrqa-labels.jsonl"
          >
            <Download size={12} aria-hidden /> Export .jsonl
          </a>
        </div>
      </div>

      {/* Progress bar */}
      {data && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, color: "var(--fg-4)", marginBottom: 4, fontFamily: "var(--mono)" }}>
            <span>{data.total} findings</span>
            <span>{labelled} labelled · {data.total - labelled} remaining</span>
          </div>
          <div className="risk-bar-track" style={{ height: 6 }}>
            <div className="risk-bar-fill" style={{ width: `${progress}%`, background: "var(--accent-2)" }} />
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="fleet-loading">Loading findings…</div>
      ) : findings.length === 0 ? (
        <div style={{ color: "var(--fg-5)", fontSize: 13, padding: "20px 0", textAlign: "center" }}>
          {unlabelledOnly ? "All findings labelled! Export your dataset." : "No findings found."}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {findings.map((f) => (
            <div key={f.id} className={`label-card${f.ground_truth ? " labelled" : ""}`}>
              <div className="label-card-head">
                <span className={`sev ${f.canonical_severity === "high" ? "high" : f.canonical_severity === "medium" ? "med" : "low"}`}>
                  {f.canonical_severity?.toUpperCase() ?? "?"}
                </span>
                <span style={{ fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--fg-3)" }}>{f.canonical_rule_id}</span>
                <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-5)" }}>
                  {f.file_path.split("/").slice(-2).join("/")}:{f.line_number ?? "?"}
                </span>
                {f.confidence_score != null && (
                  <span style={{ fontSize: 10.5, color: "var(--fg-5)", fontFamily: "var(--mono)", marginLeft: "auto" }}>
                    conf {(f.confidence_score * 100).toFixed(0)}%
                  </span>
                )}
                {f.ground_truth && (
                  <span className={`gt-badge ${f.ground_truth.toLowerCase()}`}>{f.ground_truth}</span>
                )}
              </div>
              <div style={{ fontSize: 12, color: "var(--fg-3)", margin: "6px 0 8px", lineHeight: 1.5 }}>
                {f.message.slice(0, 180)}
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                {GT_LABELS.map(({ key, label, color, icon }) => (
                  <button
                    key={key}
                    className={`gt-btn${f.ground_truth === key ? " active" : ""}`}
                    style={{ "--gt-color": color } as React.CSSProperties}
                    onClick={() => setLabel({ id: f.id, gt: key, reasoning: reasoning[f.id] })}
                    disabled={isPending}
                    title={label}
                    aria-label={`Label as ${label}`}
                  >
                    {icon} {key}
                  </button>
                ))}
                <input
                  className="label-reasoning"
                  type="text"
                  placeholder="Optional reasoning…"
                  value={reasoning[f.id] ?? ""}
                  onChange={(e) => setReasoning((prev) => ({ ...prev, [f.id]: e.target.value }))}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Rule Editor tab ───────────────────────────────────────────────────────────

const RULE_TEMPLATE = `rules:
  - id: CUSTOM-001
    patterns:
      - pattern: |
          $FUNC($X)
    message: |
      Custom pattern matched $FUNC call with $X
    languages: [python]
    severity: WARNING
    metadata:
      category: security
      cwe: CWE-XXX
`;

function RuleEditorTab() {
  const [yaml, setYaml] = useState(RULE_TEMPLATE);
  const [preview, setPreview] = useState<string | null>(null);

  const mockPreview = useCallback(() => {
    const idMatch = yaml.match(/id:\s*(\S+)/);
    const patternMatch = yaml.match(/pattern:\s*\|?\s*\n\s+(.+)/);
    const id = idMatch?.[1] ?? "CUSTOM-001";
    const pattern = patternMatch?.[1]?.trim() ?? "(no pattern)";
    setPreview(
      `Rule: ${id}\n` +
      `Pattern: ${pattern}\n\n` +
      `This rule would be evaluated by the Semgrep engine.\n` +
      `To test against a real repo, save this YAML to config/custom_rules/\n` +
      `and run: python CORE/main.py --target-dir <path> --repo-name test`
    );
  }, [yaml]);

  const downloadRule = useCallback(() => {
    const blob = new Blob([yaml], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "custom-rule.yml";
    a.click();
    URL.revokeObjectURL(url);
  }, [yaml]);

  return (
    <div className="wb-tab-body">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 16, alignItems: "start" }}>
        <div className="panel">
          <div className="panel-head">
            <span className="panel-title">Semgrep Rule YAML</span>
            <span className="panel-sub">custom detection rule</span>
          </div>
          <textarea
            className="rule-editor-textarea"
            value={yaml}
            onChange={(e) => { setYaml(e.target.value); setPreview(null); }}
            spellCheck={false}
            aria-label="Semgrep rule YAML editor"
          />
          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <button className="btn-prim" style={{ gap: 6 }} onClick={mockPreview}>
              <Play size={12} aria-hidden /> Preview
            </button>
            <button className="btn-ghost" style={{ gap: 6 }} onClick={downloadRule}>
              <Download size={12} aria-hidden /> Download YAML
            </button>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <span className="panel-title">Preview</span>
          </div>
          {preview ? (
            <pre className="rule-preview">{preview}</pre>
          ) : (
            <div style={{ color: "var(--fg-5)", fontSize: 12 }}>
              Click Preview to validate rule structure.
            </div>
          )}
          <div style={{ marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
            <div style={{ fontSize: 11.5, color: "var(--fg-4)", marginBottom: 8 }}>Quick templates:</div>
            {[
              { name: "SQL Injection",   pattern: `  - pattern: $CURSOR.execute("..." + $INPUT)` },
              { name: "Hardcoded Secret",pattern: `  - pattern: password = "..."` },
              { name: "Command Inject",  pattern: `  - pattern: subprocess.call($INPUT, shell=True)` },
            ].map(({ name, pattern }) => (
              <button key={name} className="wb-template-btn"
                      onClick={() => setYaml(RULE_TEMPLATE.replace(/ {2}- pattern:.*\n\s+\$FUNC.*/, pattern))}>
                {name}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── API Console tab ───────────────────────────────────────────────────────────

const API_ENDPOINTS = [
  { method: "GET",  path: "/v1/fleet",                      desc: "Fleet posture summary" },
  { method: "GET",  path: "/v1/vulnerabilities",            desc: "List vulnerabilities" },
  { method: "GET",  path: "/v1/workbench/query",            desc: "Parameterized query" },
  { method: "GET",  path: "/v1/workbench/rule-performance", desc: "Rule fire/TP/FP stats" },
  { method: "GET",  path: "/v1/inbox",                      desc: "Inbox feed" },
  { method: "GET",  path: "/v1/fleet/compliance",           desc: "OWASP compliance matrix" },
  { method: "GET",  path: "/v1/search?q=",                  desc: "Cross-object search" },
  { method: "POST", path: "/v1/workbench/nl-query",         desc: "Natural language query" },
  { method: "GET",  path: "/v1/workbench/labels/export",    desc: "Export labelled .jsonl" },
  { method: "GET",  path: "/health",                        desc: "Liveness probe" },
];

function APIConsoleTab() {
  const [selected, setSelected] = useState(API_ENDPOINTS[0]);
  const [customPath, setCustomPath] = useState(selected.path);
  const [body, setBody] = useState("{}");
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    setResponse(null);
    try {
      const token = JSON.parse(localStorage.getItem("acrqa:auth") || "{}").token ?? "";
      const opts: RequestInit = {
        method: selected.method,
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      };
      if (selected.method === "POST") opts.body = body;
      const res = await fetch(customPath, opts);
      const text = await res.text();
      try {
        setResponse(JSON.stringify(JSON.parse(text), null, 2));
      } catch {
        setResponse(text);
      }
    } catch (e) {
      setResponse(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="wb-tab-body">
      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16 }}>
        {/* Endpoint list */}
        <div className="panel">
          <div className="panel-head"><span className="panel-title">Endpoints</span></div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {API_ENDPOINTS.map((ep) => (
              <button
                key={ep.path}
                className={`api-ep-btn${selected.path === ep.path ? " on" : ""}`}
                onClick={() => { setSelected(ep); setCustomPath(ep.path); }}
              >
                <span className={`api-method ${ep.method.toLowerCase()}`}>{ep.method}</span>
                <span className="api-path">{ep.path.length > 32 ? ep.path.slice(0, 32) + "…" : ep.path}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Request + Response */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="panel">
            <div className="panel-head">
              <span className="panel-title">{selected.desc}</span>
              <span className={`api-method ${selected.method.toLowerCase()}`} style={{ marginLeft: 8 }}>{selected.method}</span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: selected.method === "POST" ? 10 : 0 }}>
              <input
                className="cmd-input"
                style={{ flex: 1, border: "1px solid var(--border)", borderRadius: 6, padding: "6px 10px", fontSize: 12.5, fontFamily: "var(--mono)", color: "var(--fg-2)", background: "var(--bg-3)" }}
                value={customPath}
                onChange={(e) => setCustomPath(e.target.value)}
                aria-label="API path"
              />
              <button className="btn-prim" style={{ gap: 6, whiteSpace: "nowrap" }} onClick={run} disabled={loading}>
                <Play size={12} aria-hidden /> {loading ? "Running…" : "Run"}
              </button>
            </div>
            {selected.method === "POST" && (
              <textarea
                className="rule-editor-textarea"
                style={{ height: 80, marginTop: 8 }}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                aria-label="Request body"
              />
            )}
          </div>

          <div className="panel">
            <div className="panel-head">
              <span className="panel-title">Response</span>
            </div>
            {response ? (
              <pre className="api-response">{response}</pre>
            ) : (
              <div style={{ color: "var(--fg-5)", fontSize: 12 }}>Hit Run to see response.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Triage Chat tab (5.11) ────────────────────────────────────────────────────

type ChatMsg = { role: "user" | "assistant"; text: string };

function TriageChatTab() {
  const [messages, setMessages] = useState<ChatMsg[]>([
    { role: "assistant", text: "I can help triage findings. Ask me anything — I'll scope my analysis to your current query filters. Try: \"Show me high severity injection findings in auth.py\" or \"Which rules have the highest false positive rate?\"" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [useLLM, setUseLLM] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMsg }]);
    setLoading(true);

    try {
      const res = await api.wbNLQuery(userMsg, useLLM);
      const parsed = res.parsed;
      const filtersText = Object.entries(parsed)
        .filter(([, v]) => v != null && v !== "" && v !== 50)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ") || "none (showing all)";

      const countText = res.total === 0
        ? "No vulnerabilities found matching those criteria."
        : `Found **${res.total}** vulnerabilities. Showing top ${res.results.length}.`;

      const topItems = res.results.slice(0, 5).map((r) =>
        `• \`${r.short_id}\` ${r.canonical_rule_id} · ${r.severity} · ${r.file_path.split("/").slice(-1)[0]}`
      ).join("\n");

      setMessages((prev) => [...prev, {
        role: "assistant",
        text: `Parsed filters: ${filtersText}\n\n${countText}${topItems ? "\n\n" + topItems : ""}`,
      }]);
    } catch {
      setMessages((prev) => [...prev, {
        role: "assistant",
        text: "Query failed. Check that the API server is running.",
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  return (
    <div className="wb-tab-body">
      <div className="panel" style={{ display: "flex", flexDirection: "column", height: "60vh", minHeight: 400 }}>
        <div className="panel-head">
          <span className="panel-title">Triage Chat</span>
          <span className="panel-sub">NL → parameterized query · scoped to your DB</span>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--fg-4)" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 5, cursor: "pointer" }}>
              <input type="checkbox" checked={useLLM} onChange={(e) => setUseLLM(e.target.checked)}
                     style={{ accentColor: "var(--accent-2)" }} />
              Use LLM parser (Groq)
            </label>
          </div>
        </div>
        <div className="chat-messages">
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg ${m.role}`}>
              <pre className="chat-msg-text">{m.text}</pre>
            </div>
          ))}
          {loading && (
            <div className="chat-msg assistant">
              <span className="spinner" style={{ width: 14, height: 14 }} aria-label="Thinking" />
            </div>
          )}
          <div ref={endRef} />
        </div>
        <div className="chat-input-row">
          <input
            className="cmd-input"
            style={{ flex: 1, border: "1px solid var(--border)", borderRadius: 6, padding: "8px 12px", fontSize: 13 }}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Ask about findings… (Enter to send)"
            aria-label="Triage chat input"
          />
          <button className="btn-prim" style={{ gap: 6 }} onClick={send} disabled={loading}>
            <Play size={12} aria-hidden /> Send
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Workbench page ───────────────────────────────────────────────────────

export function WorkbenchPage() {
  const [activeTab, setActiveTab] = useState<TabId>("query");
  const [cells, setCells] = useState<Cell[]>([newCell()]);
  const [savedQueries, setSavedQueries] = useState<SavedQuery[]>(loadSaved);
  const [showSaved, setShowSaved] = useState(false);
  const [nlInput, setNLInput] = useState("");
  const [nlLoading, setNLLoading] = useState(false);
  const [filters, setFilters] = useState<api.WbQueryParams>({});
  const [attackVulnId, setAttackVulnId] = useState<number | undefined>();

  const { data: runsData } = useRuns(20);
  const { data: rulePerf, isLoading: ruleLoading } = useRulePerformance(50);
  const { data: auditData, isLoading: auditLoading } = useAuditLog(100);
  const runs = runsData?.runs ?? [];

  // Quick filter form
  const [qSev, setQSev] = useState("");
  const [qRule, setQRule] = useState("");
  const [qStatus, setQStatus] = useState("");
  const [qFile, setQFile] = useState("");
  const [qOwner, setQOwner] = useState("");

  const applyFilters = () => {
    const p: api.WbQueryParams = {};
    if (qSev)    p.severity = qSev;
    if (qRule)   p.rule = qRule;
    if (qStatus) p.status = qStatus;
    if (qFile)   p.file = qFile;
    if (qOwner)  p.owner = qOwner;
    setCells((prev) => [newCell(p), ...prev]);
    setFilters(p);
  };

  const runNL = async () => {
    if (!nlInput.trim() || nlLoading) return;
    setNLLoading(true);
    try {
      const res = await api.wbNLQuery(nlInput.trim(), false);
      setCells((prev) => [newCell(res.parsed, nlInput.trim()), ...prev]);
    } catch { /* degraded */ }
    setNLLoading(false);
  };

  const saveQuery = () => {
    const name = prompt("Query name:");
    if (!name) return;
    const sq: SavedQuery = { name, params: filters, nl: nlInput || undefined };
    const updated = [sq, ...savedQueries.filter((q) => q.name !== name)].slice(0, 10);
    setSavedQueries(updated);
    persist(updated);
  };

  const loadQuery = (q: SavedQuery) => {
    setCells((prev) => [newCell(q.params, q.nl ?? ""), ...prev]);
    setShowSaved(false);
  };

  return (
    <>
      {/* Topbar */}
      <div className="topbar no-print">
        <div className="crumbs">
          <Link to="/overview" style={{ color: "var(--fg-4)", textDecoration: "none", fontSize: 13 }}>Overview</Link>
          <span style={{ color: "var(--fg-5)", margin: "0 6px" }}>/</span>
          <span className="cur">Workbench</span>
        </div>
        <div className="grow" />
        <div style={{ position: "relative" }}>
          <button className="btn-ghost" style={{ gap: 6, height: 30 }} onClick={() => setShowSaved((v) => !v)}>
            <BookmarkPlus size={13} aria-hidden /> Saved
          </button>
          {showSaved && (
            <div className="fleet-saved-menu" onClick={(e) => e.stopPropagation()}>
              <button className="fleet-saved-item fleet-saved-save" onClick={saveQuery}>
                <BookmarkPlus size={12} aria-hidden /> Save current query
              </button>
              {savedQueries.length > 0 && <div className="fleet-saved-divider" />}
              {savedQueries.map((q) => (
                <button key={q.name} className="fleet-saved-item" onClick={() => loadQuery(q)}>
                  {q.name}
                  <span style={{ fontSize: 10.5, color: "var(--fg-5)", marginLeft: "auto" }}>
                    {q.nl ? "NL" : Object.keys(q.params).length + " filters"}
                  </span>
                </button>
              ))}
              {savedQueries.length === 0 && (
                <div style={{ padding: "8px 12px", fontSize: 12, color: "var(--fg-5)" }}>No saved queries</div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="page-pad wb-page">
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 20 }}>
          <h1 className="title" style={{ margin: 0 }}>Workbench</h1>
          <span style={{ fontSize: 12, color: "var(--fg-5)" }}>power-user analysis surface</span>
        </div>

        {/* Tab bar */}
        <div className="fleet-tabs no-print" role="tablist" aria-label="Workbench tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={activeTab === t.id}
              className={`fleet-tab${activeTab === t.id ? " on" : ""}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* ── QUERY TAB ─────────────────────────────────────────────── */}
        {activeTab === "query" && (
          <div className="wb-tab-body">
            {/* NL input */}
            <div className="panel" style={{ marginBottom: 14 }}>
              <div className="panel-head">
                <span className="panel-title">Natural Language Query</span>
                <span className="panel-sub">e.g. "top 10 high SQL injection in auth.py assigned to alice"</span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  className="cmd-input"
                  style={{ flex: 1, border: "1px solid var(--border)", borderRadius: 6, padding: "7px 12px", fontSize: 13, background: "var(--bg-3)", color: "var(--fg)" }}
                  value={nlInput}
                  onChange={(e) => setNLInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && runNL()}
                  placeholder="Describe what you're looking for…"
                  aria-label="Natural language query"
                />
                <button className="btn-prim" style={{ gap: 6 }} onClick={runNL} disabled={nlLoading}>
                  <Search size={12} aria-hidden /> {nlLoading ? "Parsing…" : "Query"}
                </button>
              </div>
            </div>

            {/* Quick filters */}
            <div className="panel" style={{ marginBottom: 14 }}>
              <div className="panel-head">
                <span className="panel-title">Filter</span>
                <span className="panel-sub">parameterized — no raw SQL</span>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
                {[
                  { lbl: "Severity", val: qSev, set: setQSev, opts: ["", "high", "medium", "low"] },
                  { lbl: "Status",   val: qStatus, set: setQStatus, opts: ["", "detected", "confirmed", "assigned", "in_progress", "fixed", "dismissed", "regressed"] },
                ].map(({ lbl, val, set, opts }) => (
                  <div key={lbl} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <label style={{ fontSize: 10.5, color: "var(--fg-5)", textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: "var(--mono)" }}>{lbl}</label>
                    <select className="fleet-repo-select" value={val} onChange={(e) => set(e.target.value)}>
                      {opts.map((o) => <option key={o} value={o}>{o || "any"}</option>)}
                    </select>
                  </div>
                ))}
                {[
                  { lbl: "Rule",  val: qRule, set: setQRule, ph: "SECURITY-001" },
                  { lbl: "File",  val: qFile, set: setQFile, ph: "auth.py" },
                  { lbl: "Owner", val: qOwner, set: setQOwner, ph: "alice" },
                ].map(({ lbl, val, set, ph }) => (
                  <div key={lbl} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <label style={{ fontSize: 10.5, color: "var(--fg-5)", textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: "var(--mono)" }}>{lbl}</label>
                    <input
                      className="cmd-input"
                      style={{ width: 130, border: "1px solid var(--border)", borderRadius: 6, padding: "6px 10px", fontSize: 12, background: "var(--bg-3)", color: "var(--fg)" }}
                      value={val}
                      onChange={(e) => set(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && applyFilters()}
                      placeholder={ph}
                    />
                  </div>
                ))}
                <button className="btn-prim" style={{ gap: 6, alignSelf: "flex-end" }} onClick={applyFilters}>
                  <Play size={12} aria-hidden /> Run
                </button>
                <button className="btn-ghost" style={{ gap: 6, alignSelf: "flex-end" }}
                        onClick={() => setCells((p) => [newCell(), ...p])}>
                  + Cell
                </button>
              </div>
            </div>

            {/* Notebook cells */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {cells.map((c) => (
                <QueryCell key={c.id} cell={c}
                           onRemove={() => setCells((p) => p.filter((x) => x.id !== c.id))} />
              ))}
            </div>

            {/* Attack path panel */}
            {attackVulnId && (
              <div className="panel" style={{ marginTop: 16 }}>
                <div className="panel-head">
                  <span className="panel-title">Attack Path</span>
                  <span className="panel-sub">taint chain from vuln #{attackVulnId}</span>
                  <button className="btn-ghost" style={{ marginLeft: "auto", height: 26, fontSize: 11 }}
                          onClick={() => setAttackVulnId(undefined)}>clear</button>
                </div>
                <AttackPath vulnId={attackVulnId} />
              </div>
            )}
          </div>
        )}

        {/* ── RULE PERF TAB ─────────────────────────────────────────── */}
        {activeTab === "rules" && (
          <div className="wb-tab-body">
            <div className="panel">
              <div className="panel-head">
                <span className="panel-title">Rule Performance</span>
                <span className="panel-sub">{rulePerf?.total ?? 0} rules · fire rate · TP/FP accuracy</span>
              </div>
              {ruleLoading ? <div className="fleet-loading">Loading…</div> : (
                <table className="wb-table" role="table">
                  <thead>
                    <tr>
                      <th>Rule ID</th><th>Fires</th><th>TP</th><th>FP</th>
                      <th>TP Rate</th><th>Noise</th><th>Labelled</th>
                      <th>GT Acc</th><th>Avg Conf</th><th>Runs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(rulePerf?.rules ?? []).map((r) => (
                      <tr key={r.rule_id} className="wb-row">
                        <td><span style={{ fontFamily: "var(--mono)", fontSize: 11.5 }}>{r.rule_id}</span></td>
                        <td><CountUp value={r.fire_count} /></td>
                        <td><span style={{ color: "var(--sev-low)", fontFamily: "var(--mono)" }}>{r.tp_count}</span></td>
                        <td><span style={{ color: "var(--sev-high)", fontFamily: "var(--mono)" }}>{r.fp_count}</span></td>
                        <td>
                          {r.tp_rate != null ? (
                            <span style={{ fontFamily: "var(--mono)", color: r.tp_rate >= 0.8 ? "var(--sev-low)" : r.tp_rate >= 0.5 ? "var(--sev-medium)" : "var(--sev-high)" }}>
                              {(r.tp_rate * 100).toFixed(0)}%
                            </span>
                          ) : <span style={{ color: "var(--fg-5)" }}>—</span>}
                        </td>
                        <td>
                          <span style={{ fontFamily: "var(--mono)", fontSize: 11.5, color: r.noise_ratio > 0.3 ? "var(--sev-high)" : "var(--fg-3)" }}>
                            {(r.noise_ratio * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td><span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>{r.labelled_count}</span></td>
                        <td>
                          {r.gt_accuracy != null ? (
                            <span style={{ fontFamily: "var(--mono)", fontSize: 11.5, color: r.gt_accuracy >= 0.8 ? "var(--sev-low)" : "var(--sev-medium)" }}>
                              {(r.gt_accuracy * 100).toFixed(0)}%
                            </span>
                          ) : <span style={{ color: "var(--fg-5)" }}>—</span>}
                        </td>
                        <td><span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>{(r.avg_confidence * 100).toFixed(0)}%</span></td>
                        <td><span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-5)" }}>{r.runs_seen}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {/* ── AUDIT LOG TAB ─────────────────────────────────────────── */}
        {activeTab === "audit" && (
          <div className="wb-tab-body">
            <div className="panel">
              <div className="panel-head">
                <span className="panel-title">Audit Log</span>
                <span className="panel-sub">{auditData?.total ?? 0} events · vulnerability lifecycle</span>
              </div>
              {auditLoading ? <div className="fleet-loading">Loading…</div> : (
                <div className="timeline">
                  {(auditData?.events ?? []).slice(0, 80).map((ev, i) => (
                    <div key={i} className="timeline-event">
                      <div className={`timeline-dot ${ev.severity ?? "low"}`} />
                      <div className="timeline-body">
                        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                          <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>{ev.short_id ?? "—"}</span>
                          <span style={{ fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--fg-2)" }}>{ev.canonical_rule_id ?? "—"}</span>
                          {ev.severity && <span className={`sev ${ev.severity === "high" ? "high" : ev.severity === "medium" ? "med" : "low"}`}>{ev.severity.toUpperCase()}</span>}
                          {ev.status && <span className={`vuln-status ${ev.status}`}>{ev.status}</span>}
                          {ev.triage_verdict && (
                            <span className={`gt-badge ${ev.triage_verdict.toLowerCase()}`}>{ev.triage_verdict}</span>
                          )}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--fg-5)", marginTop: 2, fontFamily: "var(--mono)" }}>
                          {ev.repo_name} · {ev.file_path ? ev.file_path.split("/").slice(-2).join("/") : "—"} · {ev.event_at.slice(0, 16).replace("T", " ")}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── LABELLING TAB ─────────────────────────────────────────── */}
        {activeTab === "labelling" && <LabellingTab />}

        {/* ── RULE EDITOR TAB ───────────────────────────────────────── */}
        {activeTab === "editor" && <RuleEditorTab />}

        {/* ── API CONSOLE TAB ───────────────────────────────────────── */}
        {activeTab === "api" && <APIConsoleTab />}

        {/* ── TRIAGE CHAT TAB ───────────────────────────────────────── */}
        {activeTab === "chat" && <TriageChatTab />}
      </div>

      <StatusBar items={[
        { label: "Runs", value: runs.length },
        { label: "Rules", value: rulePerf?.total ?? 0 },
        { label: "Events", value: auditData?.total ?? 0 },
      ]} />
    </>
  );
}
