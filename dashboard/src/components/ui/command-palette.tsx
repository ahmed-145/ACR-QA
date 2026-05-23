import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, LayoutDashboard, Package, Settings, LogOut, GitCompare,
  BarChart2, Brain, DollarSign, GitBranch, Shield, List, Home, Inbox, Map, Terminal,
  AlertTriangle, FileCode, User,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useSearch } from "@/lib/queries";

type Command = {
  id: string;
  label: string;
  sub?: string;
  icon: React.ReactNode;
  action: () => void;
};

const NAV_COMMANDS = (navigate: ReturnType<typeof useNavigate>, logout: () => void): Command[] => [
  { id: "inbox",       label: "Go to Inbox",         icon: <Inbox size={14} aria-hidden />,         action: () => navigate("/inbox") },
  { id: "fleet",       label: "Go to Fleet",         icon: <Map size={14} aria-hidden />,           action: () => navigate("/fleet") },
  { id: "workbench",   label: "Go to Workbench",     icon: <Terminal size={14} aria-hidden />,       action: () => navigate("/workbench") },
  { id: "overview",    label: "Go to Overview",       icon: <Home size={14} aria-hidden />,           action: () => navigate("/overview") },
  { id: "scans",       label: "Go to Scans",          icon: <LayoutDashboard size={14} aria-hidden />, action: () => navigate("/scans") },
  { id: "findings",    label: "Go to All Findings",   icon: <Search size={14} aria-hidden />,         action: () => navigate("/findings") },
  { id: "vulns",       label: "Go to Vulnerabilities",icon: <Shield size={14} aria-hidden />,         action: () => navigate("/vulnerabilities") },
  { id: "repos",       label: "Go to Repositories",   icon: <GitBranch size={14} aria-hidden />,      action: () => navigate("/repos") },
  { id: "compare",     label: "Go to Compare",        icon: <GitCompare size={14} aria-hidden />,     action: () => navigate("/compare") },
  { id: "supply",      label: "Go to Supply Chain",   icon: <Package size={14} aria-hidden />,        action: () => navigate("/supply-chain") },
  { id: "analytics",   label: "Go to Analytics",      icon: <BarChart2 size={14} aria-hidden />,      action: () => navigate("/analytics") },
  { id: "ai-detect",   label: "Go to AI Detector",    icon: <Brain size={14} aria-hidden />,          action: () => navigate("/ai-detect") },
  { id: "cost",        label: "Go to Cost & ROI",     icon: <DollarSign size={14} aria-hidden />,     action: () => navigate("/cost") },
  { id: "rules",       label: "Go to Rules Browser",  icon: <List size={14} aria-hidden />,           action: () => navigate("/rules") },
  { id: "policy",      label: "Go to Policy",         icon: <Shield size={14} aria-hidden />,         action: () => navigate("/policy") },
  { id: "settings",    label: "Go to Settings",       icon: <Settings size={14} aria-hidden />,       action: () => navigate("/settings") },
  { id: "logout",      label: "Sign out",             icon: <LogOut size={14} aria-hidden />,         action: () => { logout(); navigate("/login"); } },
];

const SEV_COLOR: Record<string, string> = { high: "var(--sev-high)", medium: "var(--sev-medium)", low: "var(--sev-low)" };

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { logout } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);

  const navCommands = NAV_COMMANDS(navigate, logout);

  // Live search — fires when query >= 2 chars
  const { data: searchData } = useSearch(query);

  // Build the displayed list
  const liveResults: Command[] = [];
  if (searchData && query.trim().length >= 2) {
    for (const v of searchData.vulns.slice(0, 5)) {
      liveResults.push({
        id: `v-${v.short_id}`,
        label: v.short_id,
        sub: `${v.canonical_rule_id} · ${v.file_path.split("/").slice(-1)[0]}`,
        icon: <AlertTriangle size={14} aria-hidden style={{ color: SEV_COLOR[v.severity] }} />,
        action: () => navigate(`/vuln/${v.short_id}`),
      });
    }
    for (const r of searchData.rules.slice(0, 3)) {
      liveResults.push({
        id: `r-${r.canonical_rule_id}`,
        label: r.canonical_rule_id,
        sub: `${r.open_count} open`,
        icon: <FileCode size={14} aria-hidden style={{ color: "var(--accent-2)" }} />,
        action: () => navigate(`/findings?rule=${encodeURIComponent(r.canonical_rule_id)}`),
      });
    }
    for (const a of searchData.authors.slice(0, 3)) {
      liveResults.push({
        id: `a-${a.owner}`,
        label: a.owner,
        sub: `${a.open_count} open`,
        icon: <User size={14} aria-hidden style={{ color: "var(--fg-3)" }} />,
        action: () => navigate(`/vulnerabilities?owner=${encodeURIComponent(a.owner)}`),
      });
    }
  }

  const navFiltered = query
    ? navCommands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : navCommands;

  // Live results first (if any), then nav commands
  const filtered: Command[] = liveResults.length > 0
    ? [...liveResults, ...navFiltered]
    : navFiltered;

  const [highlighted, setHighlighted] = useState(0);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
        setQuery("");
        setHighlighted(0);
      }
      if (e.key === "/" && !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        setOpen(true);
        setQuery("");
        setHighlighted(0);
      }
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (!open) return;
    const raf = requestAnimationFrame(() => { inputRef.current?.focus(); });
    return () => cancelAnimationFrame(raf);
  }, [open]);

  // Reset highlight when results change
  useEffect(() => { setHighlighted(0); }, [query]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((h) => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter" && filtered[highlighted]) {
      filtered[highlighted].action();
      setOpen(false);
    }
  }

  if (!open) return null;

  const hasLive = liveResults.length > 0;

  return (
    <div className="cmd-bg" onClick={() => setOpen(false)}>
      <div
        className="cmd-box"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="cmd-input-row">
          <Search size={14} style={{ color: "var(--fg-4)", flexShrink: 0 }} aria-hidden />
          <input
            ref={inputRef}
            className="cmd-input"
            value={query}
            onChange={(e) => { setQuery(e.target.value); }}
            placeholder="Search vulns, rules, authors or type a command…"
          />
          <span className="kbd">ESC</span>
        </div>
        <div className="cmd-list">
          {filtered.length === 0 ? (
            <div style={{ padding: "12px 16px", fontSize: 13, color: "var(--fg-4)" }}>No results</div>
          ) : (
            <>
              {hasLive && (
                <div className="cmd-section-label">Results</div>
              )}
              {filtered.map((cmd, i) => {
                const isNav = hasLive && i === liveResults.length;
                return (
                  <div key={cmd.id}>
                    {isNav && <div className="cmd-section-label">Navigation</div>}
                    <button
                      className={`cmd-item${i === highlighted ? " on" : ""}`}
                      onClick={() => { cmd.action(); setOpen(false); }}
                      onMouseEnter={() => setHighlighted(i)}
                      style={{ width: "100%", background: "none", border: "none" }}
                    >
                      {cmd.icon}
                      <span style={{ flex: 1, textAlign: "left" }}>{cmd.label}</span>
                      {cmd.sub && (
                        <span style={{ fontSize: 11, color: "var(--fg-4)", marginLeft: 8 }}>{cmd.sub}</span>
                      )}
                    </button>
                  </div>
                );
              })}
            </>
          )}
        </div>
        <div className="cmd-footer">
          <span><span className="kbd">↑↓</span> navigate</span>
          <span><span className="kbd">↵</span> select</span>
          <span><span className="kbd">Esc</span> close</span>
        </div>
      </div>
    </div>
  );
}
