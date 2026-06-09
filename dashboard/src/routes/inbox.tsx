import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useInbox, useBulkPatch, usePatchVulnStatus, usePatchVulnOwner } from "@/lib/queries";
import { type Vulnerability, type VulnStatus } from "@/lib/api";
import { useShortcuts } from "@/lib/useShortcuts";
import { useAuth } from "@/lib/auth";
import { KbdHint } from "@/components/ui/KbdHint";
import { CheckCircle, GitPullRequest, AlertTriangle, Clock, User, RefreshCw } from "lucide-react";

// ── Section config ────────────────────────────────────────────────────────────

type SectionKey = "regressions" | "stale_tps" | "disagreements" | "new_vulns" | "assigned_to_me" | "pr_vulns";

const SECTION_META: Record<SectionKey, { label: string; cls: string; icon: React.ReactNode; description: string }> = {
  regressions:   { label: "Regressions",       cls: "regression",   icon: <AlertTriangle size={12} aria-hidden />, description: "Fixed vulns that came back" },
  stale_tps:     { label: "Stale — needs fix",  cls: "stale",        icon: <Clock size={12} aria-hidden />,         description: "Confirmed real, untouched too long" },
  disagreements: { label: "Review needed",      cls: "disagreement", icon: <RefreshCw size={12} aria-hidden />,     description: "Models disagree — human call required" },
  new_vulns:     { label: "New",                cls: "new",          icon: <CheckCircle size={12} aria-hidden />,   description: "Detected in the last 14 days" },
  assigned_to_me:{ label: "Assigned to me",     cls: "mine",         icon: <User size={12} aria-hidden />,          description: "Vulns you own" },
  pr_vulns:      { label: "PR Risk",            cls: "pr",           icon: <GitPullRequest size={12} aria-hidden />,description: "Linked to open pull requests" },
};

const SECTION_ORDER: SectionKey[] = [
  "regressions", "stale_tps", "disagreements", "new_vulns", "assigned_to_me", "pr_vulns",
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const ms = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(ms / 86_400_000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

// Flatten all inbox items into a single ordered list with section labels
function flattenInbox(data: Record<SectionKey, Vulnerability[]>): Array<{ vuln: Vulnerability; section: SectionKey }> {
  const items: Array<{ vuln: Vulnerability; section: SectionKey }> = [];
  const seen = new Set<number>();
  for (const key of SECTION_ORDER) {
    for (const v of data[key] ?? []) {
      if (!seen.has(v.id)) {
        seen.add(v.id);
        items.push({ vuln: v, section: key });
      }
    }
  }
  return items;
}

// ── Owner assign modal ────────────────────────────────────────────────────────

function AssignModal({
  vulnIds, onClose, onAssign,
}: { vulnIds: number[]; onClose: () => void; onAssign: (owner: string | null) => void }) {
  const [val, setVal] = useState("");
  return (
    <div
      style={{ position: "fixed", inset: 0, zIndex: 200, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="panel" style={{ width: 360, padding: "24px", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fg)" }}>
          Assign {vulnIds.length} vuln{vulnIds.length !== 1 ? "s" : ""}
        </div>
        <input
          autoFocus
          className="inp"
          placeholder="username or email"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") { onAssign(val.trim() || null); onClose(); }
            if (e.key === "Escape") onClose();
          }}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-prim" onClick={() => { onAssign(val.trim() || null); onClose(); }}>Assign</button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function InboxPage() {
  useAuth();
  const navigate = useNavigate();
  const { data, isLoading, refetch } = useInbox();
  const bulkPatch = useBulkPatch();
  const patchStatus = usePatchVulnStatus();
  const patchOwner = usePatchVulnOwner();

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [cursorIdx, setCursorIdx] = useState(0);
  const [assignOpen, setAssignOpen] = useState(false);
  const [activeLens, setActiveLens] = useState<SectionKey | "all">("all");

  const allItems = data
    ? flattenInbox(data as unknown as Record<SectionKey, Vulnerability[]>)
    : [];

  const visibleItems = activeLens === "all"
    ? allItems
    : allItems.filter((i) => i.section === activeLens);

  const isEmpty = !isLoading && data?.total === 0;
  const hasSelected = selected.size > 0;

  // Request desktop notification permission on mount
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  // Fire desktop notification when regressions appear
  const prevRegressionCount = useRef(0);
  useEffect(() => {
    const count = data?.regressions?.length ?? 0;
    if (count > prevRegressionCount.current && prevRegressionCount.current !== 0) {
      if ("Notification" in window && Notification.permission === "granted") {
        new Notification("ACR-QA — Regression detected", {
          body: `${count} vulnerability${count !== 1 ? "ies" : "y"} regressed since last check.`,
        });
      }
    }
    prevRegressionCount.current = count;
  }, [data?.regressions?.length]);

  // ── Keyboard helpers ────────────────────────────────────────────────────────

  const cursorVuln = visibleItems[cursorIdx]?.vuln;

  const toggleSelect = useCallback((id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const singleStatus = useCallback((s: VulnStatus) => {
    if (!cursorVuln) return;
    patchStatus.mutate({ vulnId: cursorVuln.id, status: s });
  }, [cursorVuln, patchStatus]);

  const bulkStatus = useCallback((s: VulnStatus) => {
    if (!hasSelected) return;
    bulkPatch.mutate({ vuln_ids: Array.from(selected), status: s });
    setSelected(new Set());
  }, [selected, hasSelected, bulkPatch]);

  useShortcuts([
    { key: "j", handler: () => setCursorIdx((i) => Math.min(i + 1, visibleItems.length - 1)) },
    { key: "k", handler: () => setCursorIdx((i) => Math.max(i - 1, 0)) },
    { key: "x", handler: () => { if (cursorVuln) toggleSelect(cursorVuln.id); } },
    { key: "e", handler: () => { if (cursorVuln) navigate(`/vuln/${cursorVuln.short_id}`); } },
    { key: "Enter", handler: () => { if (cursorVuln) navigate(`/vuln/${cursorVuln.short_id}`); } },
    { key: "t", handler: () => hasSelected ? bulkStatus("confirmed") : singleStatus("confirmed") },
    { key: "f", handler: () => hasSelected ? bulkStatus("dismissed") : singleStatus("dismissed") },
    { key: "a", handler: () => setAssignOpen(true) },
  ]);

  // ── Render ──────────────────────────────────────────────────────────────────

  // Section counts from data
  const sectionCounts: Record<SectionKey, number> = {
    regressions:    data?.regressions?.length ?? 0,
    stale_tps:      data?.stale_tps?.length ?? 0,
    disagreements:  data?.disagreements?.length ?? 0,
    new_vulns:      data?.new_vulns?.length ?? 0,
    assigned_to_me: data?.assigned_to_me?.length ?? 0,
    pr_vulns:       data?.pr_vulns?.length ?? 0,
  };

  return (
    <>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Inbox</span>
        </div>
        <span className="grow" />
        {data && (
          <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>
            {data.total} item{data.total !== 1 ? "s" : ""}
          </span>
        )}
        <button className="btn-ghost" style={{ fontSize: 12 }} onClick={() => refetch()} aria-label="Refresh inbox">
          <RefreshCw size={12} aria-hidden /> Refresh
        </button>
        <KbdHint shortcut={["j", "k"]} label="navigate" />
        <KbdHint shortcut="e" label="open" />
        <KbdHint shortcut="x" label="select" />
        <KbdHint shortcut="t" label="confirm" />
        <KbdHint shortcut="f" label="dismiss" />
      </div>

      {/* Lens filter tabs */}
      <div style={{ borderBottom: "1px solid var(--border)", padding: "0 24px", background: "var(--bg-2)" }}>
        <div className="tabs" style={{ margin: 0, borderBottom: "none", gap: 0 }}>
          <button
            className={`tab${activeLens === "all" ? " on" : ""}`}
            onClick={() => { setActiveLens("all"); setCursorIdx(0); }}
            style={{ fontSize: 12 }}
          >
            All
            {data && data.total > 0 && (
              <span style={{ marginLeft: 6, fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)" }}>
                {data.total}
              </span>
            )}
          </button>
          {SECTION_ORDER.map((key) => {
            const meta = SECTION_META[key];
            const count = sectionCounts[key];
            if (count === 0 && activeLens !== key) return null;
            return (
              <button
                key={key}
                className={`tab${activeLens === key ? " on" : ""}`}
                onClick={() => { setActiveLens(key); setCursorIdx(0); }}
                style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 5 }}
              >
                {meta.icon}
                {meta.label}
                {count > 0 && (
                  <span className={`inbox-count ${meta.cls}`}>{count}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: "0 32px 90px" }}>
        {isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
            <span className="spinner" style={{ width: 24, height: 24 }} />
          </div>
        ) : isEmpty ? (
          <div className="inbox-empty">
            <div className="inbox-empty-icon">✓</div>
            <div className="inbox-empty-title">All caught up</div>
            <div className="inbox-empty-sub">
              No regressions, no stale TPs, no disagreements. Your codebase looks clean.
            </div>
            <Link to="/findings" className="btn-ghost" style={{ marginTop: 8, textDecoration: "none" }}>
              Browse all findings
            </Link>
          </div>
        ) : visibleItems.length === 0 ? (
          <div className="inbox-empty">
            <div className="inbox-empty-icon">✓</div>
            <div className="inbox-empty-title">Nothing here</div>
            <div className="inbox-empty-sub">No items in this category.</div>
          </div>
        ) : (
          <>
            {/* Column header — outside overflow:hidden so sticky works */}
            <div style={{
              display: "grid", gridTemplateColumns: "20px 72px 90px 1fr auto auto",
              padding: "7px 16px",
              background: "var(--bg-3)", position: "sticky", top: "53px", zIndex: 5,
              border: "1px solid var(--border)", borderBottom: "none",
              borderRadius: "12px 12px 0 0",
            }}>
              {["", "SEV", "STATUS", "FILE / MESSAGE", "AGE", "OWNER"].map((h) => (
                <div key={h} style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)", padding: "0 8px", textTransform: "uppercase", letterSpacing: "0.08em" }}>{h}</div>
              ))}
            </div>

            {/* Rows panel — border-radius only on bottom */}
            <div className="panel" style={{ padding: 0, overflow: "hidden", borderRadius: "0 0 12px 12px", borderTop: "none", marginTop: 0 }}>
              {activeLens === "all"
                ? renderGrouped(visibleItems, cursorIdx, selected, (vuln) => {
                    navigate(`/vuln/${vuln.short_id}`);
                  }, toggleSelect)
                : renderFlat(visibleItems, cursorIdx, selected, (vuln) => {
                    navigate(`/vuln/${vuln.short_id}`);
                  }, toggleSelect)
              }
            </div>
          </>
        )}
      </div>

      {/* Bulk action bar */}
      {hasSelected && (
        <div className="bulk-bar">
          <span className="bulk-bar-count">{selected.size} selected</span>
          <button
            className="btn-ghost"
            style={{ fontSize: 12 }}
            onClick={() => bulkStatus("confirmed")}
          >
            Confirm TP (T)
          </button>
          <button
            className="btn-ghost"
            style={{ fontSize: 12 }}
            onClick={() => bulkStatus("dismissed")}
          >
            Dismiss FP (F)
          </button>
          <button
            className="btn-ghost"
            style={{ fontSize: 12 }}
            onClick={() => setAssignOpen(true)}
          >
            Assign… (A)
          </button>
          <button
            className="btn-ghost"
            style={{ fontSize: 12, marginLeft: "auto" }}
            onClick={() => setSelected(new Set())}
          >
            Clear
          </button>
        </div>
      )}

      {/* Assign modal */}
      {assignOpen && (
        <AssignModal
          vulnIds={hasSelected ? Array.from(selected) : cursorVuln ? [cursorVuln.id] : []}
          onClose={() => setAssignOpen(false)}
          onAssign={(owner) => {
            const ids = hasSelected ? Array.from(selected) : cursorVuln ? [cursorVuln.id] : [];
            if (!ids.length) return;
            if (hasSelected) {
              bulkPatch.mutate({ vuln_ids: ids, owner: owner ?? undefined, clear_owner: owner === null });
              setSelected(new Set());
            } else if (cursorVuln) {
              patchOwner.mutate({ vulnId: cursorVuln.id, owner });
            }
          }}
        />
      )}
    </>
  );
}

// ── Row render helpers ────────────────────────────────────────────────────────

function VulnRow({
  vuln, isActive, isSelected, onClick, onCheck,
}: {
  vuln: Vulnerability;
  isActive: boolean;
  isSelected: boolean;
  onClick: () => void;
  onCheck: () => void;
}) {
  const sev = vuln.severity.toUpperCase();
  const sevCls = sev === "HIGH" ? "high" : sev === "MEDIUM" ? "med" : "low";
  return (
    <div
      className={`inbox-item${isActive ? " cursor" : ""}${isSelected ? " selected" : ""}`}
      onClick={onClick}
      role="row"
      aria-selected={isActive}
      tabIndex={isActive ? 0 : -1}
    >
      {/* Checkbox */}
      <div
        className={`inbox-check${isSelected ? " on" : ""}`}
        onClick={(e) => { e.stopPropagation(); onCheck(); }}
        role="checkbox"
        aria-checked={isSelected}
        aria-label="Select"
      >
        {isSelected && <span style={{ color: "#fff", fontSize: 9, fontWeight: 700 }}>✓</span>}
      </div>

      {/* Severity */}
      <div style={{ padding: "0 8px" }}>
        <span className={`sev ${sevCls}`}>{sev}</span>
      </div>

      {/* Status */}
      <div style={{ padding: "0 8px" }}>
        <span className={`vuln-status ${vuln.status}`} style={{ cursor: "default", fontSize: 10 }}>
          {vuln.status.replace("_", " ").toUpperCase()}
        </span>
      </div>

      {/* File + message */}
      <div style={{ padding: "0 12px", overflow: "hidden" }}>
        <div className="inbox-item-msg">{vuln.message ?? vuln.canonical_rule_id}</div>
        <div className="inbox-item-file">{vuln.file_path}</div>
      </div>

      {/* Age */}
      <div style={{ padding: "0 12px", fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--fg-5)", whiteSpace: "nowrap" }}>
        {timeAgo(vuln.first_seen_at)}
      </div>

      {/* Owner */}
      <div style={{ padding: "0 12px", fontSize: 11, color: "var(--fg-5)", whiteSpace: "nowrap", minWidth: 80, textAlign: "right" }}>
        {vuln.owner ?? <span style={{ color: "var(--fg-5)", opacity: 0.5 }}>—</span>}
      </div>
    </div>
  );
}

function SectionDivider({ sectionKey, count }: { sectionKey: SectionKey; count: number }) {
  const meta = SECTION_META[sectionKey];
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "8px 16px", background: "var(--bg-3)",
      borderBottom: "1px solid var(--border)",
    }}>
      <span className={`inbox-section-label ${meta.cls}`} style={{ display: "flex", alignItems: "center", gap: 5 }}>
        {meta.icon} {meta.label}
      </span>
      <span className={`inbox-count ${meta.cls}`}>{count}</span>
      <span style={{ fontSize: 11, color: "var(--fg-5)" }}>{meta.description}</span>
    </div>
  );
}

function renderGrouped(
  items: Array<{ vuln: Vulnerability; section: SectionKey }>,
  cursorIdx: number,
  selected: Set<number>,
  onOpen: (v: Vulnerability) => void,
  onCheck: (id: number) => void,
) {
  const groups: Array<{ key: SectionKey; items: Array<{ vuln: Vulnerability; globalIdx: number }> }> = [];
  let globalIdx = 0;
  for (const sectionKey of SECTION_ORDER) {
    const sectionItems = items.filter((i) => i.section === sectionKey);
    if (sectionItems.length > 0) {
      groups.push({ key: sectionKey, items: sectionItems.map((i) => ({ vuln: i.vuln, globalIdx: globalIdx++ })) });
    }
  }
  return groups.map(({ key, items: gItems }) => (
    <div key={key}>
      <SectionDivider sectionKey={key} count={gItems.length} />
      {gItems.map(({ vuln, globalIdx: gi }) => (
        <VulnRow
          key={vuln.id}
          vuln={vuln}
          isActive={gi === cursorIdx}
          isSelected={selected.has(vuln.id)}
          onClick={() => onOpen(vuln)}
          onCheck={() => onCheck(vuln.id)}
        />
      ))}
    </div>
  ));
}

function renderFlat(
  items: Array<{ vuln: Vulnerability; section: SectionKey }>,
  cursorIdx: number,
  selected: Set<number>,
  onOpen: (v: Vulnerability) => void,
  onCheck: (id: number) => void,
) {
  return items.map(({ vuln }, idx) => (
    <VulnRow
      key={vuln.id}
      vuln={vuln}
      isActive={idx === cursorIdx}
      isSelected={selected.has(vuln.id)}
      onClick={() => onOpen(vuln)}
      onCheck={() => onCheck(vuln.id)}
    />
  ));
}
