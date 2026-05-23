import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  useVulnerability, useVulnFindings,
  usePatchVulnStatus, usePatchVulnOwner, useAutofix, useAttestation,
} from "@/lib/queries";
import { type VulnStatus } from "@/lib/api";
import { RelatedObjectsPanel } from "@/components/ui/RelatedObjects";
import {
  ArrowLeft, Shield, Clock, User, ChevronDown, ExternalLink,
  GitBranch, AlertTriangle, CheckCircle, FileDown,
} from "lucide-react";

// ── Section IDs ───────────────────────────────────────────────────────────────

const SECTIONS = [
  { id: "overview",    label: "Overview" },
  { id: "timeline",    label: "Timeline" },
  { id: "code",        label: "Code Context" },
  { id: "ensemble",    label: "Ensemble" },
  { id: "related",     label: "Related" },
  { id: "fix",         label: "Fix" },
  { id: "attestation", label: "Attestation" },
  { id: "references",  label: "References" },
] as const;

// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  const ms = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(ms / 86_400_000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}yr ago`;
}

function fmtDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

const STATUS_LABELS: Record<VulnStatus, string> = {
  detected: "DETECTED", confirmed: "CONFIRMED", assigned: "ASSIGNED",
  in_progress: "IN PROGRESS", fixed: "FIXED", verified: "VERIFIED",
  regressed: "REGRESSED", dismissed: "DISMISSED",
};

const STATUS_FLOW: VulnStatus[] = [
  "detected", "confirmed", "assigned", "in_progress", "fixed", "verified", "regressed", "dismissed",
];

// CVE/CWE references derived from canonical rule IDs
const RULE_REFS: Record<string, { label: string; url: string }[]> = {
  "SECURITY-001": [{ label: "CWE-89: SQL Injection", url: "https://cwe.mitre.org/data/definitions/89.html" }],
  "SECURITY-002": [{ label: "CWE-78: OS Command Injection", url: "https://cwe.mitre.org/data/definitions/78.html" }],
  "SECURITY-003": [{ label: "CWE-79: XSS", url: "https://cwe.mitre.org/data/definitions/79.html" }],
  "SECURITY-004": [{ label: "CWE-22: Path Traversal", url: "https://cwe.mitre.org/data/definitions/22.html" }],
  "SECURITY-005": [{ label: "CWE-94: Code Injection", url: "https://cwe.mitre.org/data/definitions/94.html" }],
  "SECURITY-006": [{ label: "CWE-326: Weak Cryptography", url: "https://cwe.mitre.org/data/definitions/326.html" }],
};

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="vuln-section-title">{children}</div>;
}

function SectionCard({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div className="panel" style={{ padding: "18px 20px", ...style }}>
      {children}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function VulnDetailPage() {
  const { shortId } = useParams<{ shortId: string }>();
  const navigate = useNavigate();

  const { data: vuln, isLoading } = useVulnerability(shortId);
  const { data: findingsData } = useVulnFindings(vuln?.id);
  const findings = findingsData?.findings ?? [];

  // Latest finding for fix/attestation
  const latestFinding = findings[0];
  const latestRunId = latestFinding?.run_id ?? 0;
  const latestFindingId = latestFinding?.id ?? 0;

  const { data: autofix } = useAutofix(latestRunId, latestFindingId, !!latestFinding);
  const { data: attestation } = useAttestation(latestRunId);

  const patchStatus = usePatchVulnStatus();
  const patchOwner = usePatchVulnOwner();

  const [statusOpen, setStatusOpen] = useState(false);
  const [ownerEditing, setOwnerEditing] = useState(false);
  const [ownerInput, setOwnerInput] = useState("");
  const [activeSection, setActiveSection] = useState("overview");

  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});

  // IntersectionObserver — track which section is in view
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveSection(entry.target.id);
        }
      },
      { rootMargin: "-30% 0px -60% 0px", threshold: 0 }
    );
    Object.values(sectionRefs.current).forEach((el) => el && obs.observe(el));
    return () => obs.disconnect();
  }, [vuln]);

  const scrollTo = useCallback((id: string) => {
    sectionRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const sev = (vuln?.severity ?? "low").toUpperCase();
  const sevCls = sev === "HIGH" ? "high" : sev === "MEDIUM" ? "med" : "low";

  // ── Build timeline from findings ───────────────────────────────────────────

  type TimelineEntry = {
    key: string;
    dot: string;
    title: string;
    meta: string;
    body: string;
  };

  const timeline: TimelineEntry[] = [];
  for (const f of [...findings].reverse()) {
    timeline.push({
      key: `detect-${f.id}`,
      dot: "detection",
      title: `Detected in run #${f.run_id}`,
      meta: fmtDate(f.run_started_at) + " · " + (f.repo_name ?? ""),
      body: f.message ?? "",
    });
    if (f.triage_verdict) {
      timeline.push({
        key: `triage-${f.id}`,
        dot: f.triage_verdict === "TP" ? "triage-tp" : "triage-fp",
        title: `Triaged: ${f.triage_verdict}`,
        meta: fmtDate(f.run_started_at),
        body: f.triage_reasoning ?? "",
      });
    }
    if (f.second_opinion_primary_verdict) {
      timeline.push({
        key: `ensemble-${f.id}`,
        dot: "ensemble",
        title: `Ensemble review — ${f.second_opinion_agreement ? "models agree" : "models disagree"}`,
        meta: fmtDate(f.run_started_at),
        body: [
          f.second_opinion_primary_verdict ? `Primary: ${f.second_opinion_primary_verdict}` : "",
          f.second_opinion_secondary_verdict ? `Secondary: ${f.second_opinion_secondary_verdict}` : "",
        ].filter(Boolean).join(" · "),
      });
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh" }}>
        <span className="spinner" style={{ width: 24, height: 24 }} />
      </div>
    );
  }

  if (!vuln) {
    return (
      <div className="page-pad" style={{ textAlign: "center", paddingTop: 80 }}>
        <p style={{ color: "var(--fg-4)" }}>Vulnerability not found.</p>
        <button className="btn-ghost" onClick={() => navigate(-1)} style={{ marginTop: 16 }}>
          <ArrowLeft size={13} aria-hidden /> Go back
        </button>
      </div>
    );
  }

  const ageLabel = vuln.first_seen_at ? timeAgo(vuln.first_seen_at) : "—";
  const confidence = latestFinding?.confidence_score ?? null;
  const refs = RULE_REFS[vuln.canonical_rule_id] ?? [];

  return (
    <>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumbs">
          <button
            className="btn-ghost no-print"
            style={{ height: 28, padding: "0 8px", fontSize: 12 }}
            onClick={() => navigate(-1)}
          >
            <ArrowLeft size={12} aria-hidden />
          </button>
          <Link to="/findings" style={{ color: "var(--fg-4)", fontSize: 13 }}>Findings</Link>
          <span className="sep" style={{ color: "var(--fg-5)" }}>/</span>
          <span className="cur">Vuln {vuln.short_id}</span>
        </div>
        <span className="grow" />
        <span className={`sev ${sevCls}`}>{sev}</span>
        <button
          className="btn-ghost no-print"
          onClick={() => window.print()}
          style={{ fontSize: 12 }}
          aria-label="Print / export as PDF"
        >
          <FileDown size={13} aria-hidden /> Export PDF
        </button>
      </div>

      {/* Two-column layout */}
      <div className="vuln-layout">
        {/* Left — sticky section nav */}
        <nav className="vuln-section-nav no-print" aria-label="Page sections">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              className={`vuln-nav-item${activeSection === s.id ? " active" : ""}`}
              onClick={() => scrollTo(s.id)}
            >
              {s.label}
            </button>
          ))}
        </nav>

        {/* Right — content */}
        <div className="vuln-content">

          {/* ── OVERVIEW ─────────────────────────────────────────────────── */}
          <section
            id="overview"
            ref={(el) => { sectionRefs.current["overview"] = el; }}
            className="vuln-section"
          >
            <SectionTitle>Overview</SectionTitle>

            {/* Header card */}
            <SectionCard>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

                {/* Row 1: severity + rule + file */}
                <div style={{ display: "flex", alignItems: "flex-start", gap: 10, flexWrap: "wrap" }}>
                  <span className={`sev ${sevCls}`}>{sev}</span>
                  <span style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--fg)", fontWeight: 600 }}>
                    {vuln.canonical_rule_id}
                  </span>
                  {vuln.category && (
                    <span style={{
                      fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)",
                      padding: "2px 7px", borderRadius: 4,
                      background: "rgba(255,255,255,0.04)", border: "1px solid var(--border-2)",
                    }}>{vuln.category}</span>
                  )}
                </div>

                {/* File path */}
                <div style={{
                  fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)",
                  padding: "4px 8px", background: "var(--bg-3)", borderRadius: 5,
                  border: "1px solid var(--border)", display: "inline-block", alignSelf: "flex-start",
                }}>
                  {vuln.file_path}
                </div>

                {/* Message */}
                {vuln.message && (
                  <p style={{ fontSize: 13.5, color: "var(--fg-2)", lineHeight: 1.7, margin: 0 }}>
                    {vuln.message}
                  </p>
                )}

                {/* Row: meta chips */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>

                  {/* Status badge — clickable dropdown */}
                  <div style={{ position: "relative" }}>
                    <button
                      className={`vuln-status ${vuln.status}`}
                      onClick={() => setStatusOpen((v) => !v)}
                      aria-label="Change status"
                    >
                      {STATUS_LABELS[vuln.status]}
                      <ChevronDown size={10} aria-hidden />
                    </button>
                    {statusOpen && (
                      <div style={{
                        position: "absolute", top: "calc(100% + 4px)", left: 0, zIndex: 50,
                        background: "var(--bg-3)", border: "1px solid var(--border-2)",
                        borderRadius: 8, overflow: "hidden", minWidth: 160,
                        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
                      }}>
                        {STATUS_FLOW.map((s) => (
                          <button
                            key={s}
                            style={{
                              display: "block", width: "100%", padding: "8px 14px",
                              textAlign: "left", background: "none", border: "none",
                              fontSize: 12, fontFamily: "var(--mono)",
                              color: s === vuln.status ? "var(--purple)" : "var(--fg-3)",
                              cursor: "pointer",
                            }}
                            onMouseOver={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.04)"; }}
                            onMouseOut={(e) => { (e.currentTarget as HTMLElement).style.background = "none"; }}
                            onClick={() => {
                              patchStatus.mutate({ vulnId: vuln.id, status: s });
                              setStatusOpen(false);
                            }}
                          >
                            {STATUS_LABELS[s]}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Age */}
                  <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "var(--fg-4)" }}>
                    <Clock size={11} aria-hidden />
                    First seen {ageLabel}
                    {vuln.first_seen_at && (
                      <span style={{ color: "var(--fg-5)", fontFamily: "var(--mono)", fontSize: 10.5 }}>
                        ({fmtDate(vuln.first_seen_at)})
                      </span>
                    )}
                  </span>

                  {/* Detection count */}
                  <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "var(--fg-4)" }}>
                    <GitBranch size={11} aria-hidden />
                    {findings.length} detection{findings.length !== 1 ? "s" : ""}
                  </span>

                  {/* Confidence */}
                  {confidence != null && (
                    <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)" }}>CONF</span>
                      <div style={{ width: 48, height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 999, overflow: "hidden" }}>
                        <div style={{ height: "100%", width: `${Math.round(confidence)}%`, background: "var(--gradient)", borderRadius: 999 }} />
                      </div>
                      <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-3)", fontWeight: 600 }}>
                        {Math.round(confidence)}%
                      </span>
                    </span>
                  )}

                  {/* Owner */}
                  {ownerEditing ? (
                    <form
                      style={{ display: "flex", gap: 6 }}
                      onSubmit={(e) => {
                        e.preventDefault();
                        patchOwner.mutate({ vulnId: vuln.id, owner: ownerInput.trim() || null });
                        setOwnerEditing(false);
                      }}
                    >
                      <input
                        autoFocus
                        value={ownerInput}
                        onChange={(e) => setOwnerInput(e.target.value)}
                        placeholder="username or email"
                        className="inp inp-sm"
                        style={{ width: 180 }}
                        onKeyDown={(e) => { if (e.key === "Escape") setOwnerEditing(false); }}
                      />
                      <button type="submit" className="btn-prim" style={{ height: 28, fontSize: 11 }}>Save</button>
                      <button type="button" className="btn-ghost" style={{ height: 28, fontSize: 11 }} onClick={() => setOwnerEditing(false)}>Cancel</button>
                    </form>
                  ) : (
                    <button
                      className="owner-chip"
                      onClick={() => { setOwnerInput(vuln.owner ?? ""); setOwnerEditing(true); }}
                      aria-label={vuln.owner ? `Owner: ${vuln.owner}` : "Assign owner"}
                    >
                      <User size={11} aria-hidden />
                      {vuln.owner ?? "Unassigned"}
                    </button>
                  )}
                </div>
              </div>
            </SectionCard>
          </section>

          {/* ── TIMELINE ────────────────────────────────────────────────── */}
          <section
            id="timeline"
            ref={(el) => { sectionRefs.current["timeline"] = el; }}
            className="vuln-section"
          >
            <SectionTitle>Timeline</SectionTitle>
            {timeline.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--fg-5)" }}>No events yet.</p>
            ) : (
              <div className="timeline">
                {timeline.map((ev) => (
                  <div key={ev.key} className="timeline-event">
                    <div className={`timeline-dot ${ev.dot}`} />
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 500, color: "var(--fg-2)" }}>{ev.title}</div>
                      <div className="timeline-meta">{ev.meta}</div>
                      {ev.body && <div className="timeline-body">{ev.body}</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ── CODE CONTEXT ────────────────────────────────────────────── */}
          <section
            id="code"
            ref={(el) => { sectionRefs.current["code"] = el; }}
            className="vuln-section"
          >
            <SectionTitle>Code Context</SectionTitle>
            {latestFinding ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {/* Snippet */}
                {(() => {
                  const ev = latestFinding.evidence as Record<string, string> | null;
                  const snippet = ev?.snippet ?? ev?.code ?? "";
                  return snippet ? (
                    <div className="evidence-block">
                      <div className="evidence-header">
                        <span>CODE</span>
                        <span className="hl-file">
                          {latestFinding.file_path}{latestFinding.line_number ? `:${latestFinding.line_number}` : ""}
                        </span>
                      </div>
                      <pre className="evidence-code">{snippet}</pre>
                    </div>
                  ) : (
                    <p style={{ fontSize: 13, color: "var(--fg-5)" }}>No code snippet available.</p>
                  );
                })()}

                {/* Taint path */}
                {(latestFinding as unknown as { taint_source?: string; taint_path?: unknown[] }).taint_source && (
                  <SectionCard style={{ background: "rgba(167,139,250,0.04)", border: "1px solid rgba(167,139,250,0.15)" }}>
                    <div style={{ fontSize: 11, color: "var(--purple)", marginBottom: 8, fontFamily: "var(--mono)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                      Taint Chain
                    </div>
                    <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-3)" }}>
                      Source: {(latestFinding as unknown as { taint_source?: string }).taint_source}
                    </div>
                  </SectionCard>
                )}
              </div>
            ) : (
              <p style={{ fontSize: 13, color: "var(--fg-5)" }}>No findings loaded yet.</p>
            )}
          </section>

          {/* ── ENSEMBLE ────────────────────────────────────────────────── */}
          <section
            id="ensemble"
            ref={(el) => { sectionRefs.current["ensemble"] = el; }}
            className="vuln-section"
          >
            <SectionTitle>Ensemble — Model Votes</SectionTitle>
            {(() => {
              const withOpinion = findings.filter((f) => f.second_opinion_primary_verdict);
              if (!withOpinion.length) {
                return (
                  <p style={{ fontSize: 13, color: "var(--fg-5)" }}>
                    No ensemble data yet. Open a finding and request a 2nd Opinion from the run detail page.
                  </p>
                );
              }
              const latest = withOpinion[0];
              return (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{
                    padding: "12px 16px", borderRadius: 8,
                    background: latest.second_opinion_agreement ? "rgba(16,185,129,0.08)" : "rgba(245,158,11,0.08)",
                    border: `1px solid ${latest.second_opinion_agreement ? "rgba(16,185,129,0.25)" : "rgba(245,158,11,0.25)"}`,
                    fontSize: 13, fontWeight: 600,
                    color: latest.second_opinion_agreement ? "var(--low-fg)" : "var(--med-fg)",
                  }}>
                    {latest.second_opinion_agreement
                      ? <><CheckCircle size={14} style={{ display: "inline", marginRight: 6 }} aria-hidden />Models agree</>
                      : <><AlertTriangle size={14} style={{ display: "inline", marginRight: 6 }} aria-hidden />Models disagree — manual review recommended</>
                    }
                  </div>
                  <div className="ensemble-grid">
                    {[
                      { label: "Primary", verdict: latest.second_opinion_primary_verdict },
                      { label: "Secondary", verdict: latest.second_opinion_secondary_verdict },
                    ].map(({ label, verdict }) => verdict && (
                      <div key={label} className="ensemble-card">
                        <div className="ensemble-provider">{label}</div>
                        <div className={`ensemble-verdict sev ${verdict === "TP" ? "high" : verdict === "FP" ? "low" : "med"}`}>
                          {verdict}
                        </div>
                      </div>
                    ))}
                  </div>
                  {withOpinion.length > 1 && (
                    <p style={{ fontSize: 12, color: "var(--fg-5)" }}>
                      {withOpinion.length} ensemble reviews across {findings.length} detections.
                    </p>
                  )}
                </div>
              );
            })()}
          </section>

          {/* ── RELATED ─────────────────────────────────────────────────── */}
          <section
            id="related"
            ref={(el) => { sectionRefs.current["related"] = el; }}
            className="vuln-section"
          >
            <SectionTitle>Related Vulnerabilities</SectionTitle>
            <RelatedObjectsPanel vulnId={vuln?.id} />
          </section>

          {/* ── FIX ─────────────────────────────────────────────────────── */}
          <section
            id="fix"
            ref={(el) => { sectionRefs.current["fix"] = el; }}
            className="vuln-section"
          >
            <SectionTitle>Fix</SectionTitle>
            {!latestFinding ? (
              <p style={{ fontSize: 13, color: "var(--fg-5)" }}>No findings loaded.</p>
            ) : autofix?.patch ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 8, padding: "10px 14px",
                  borderRadius: 7, background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)",
                }}>
                  <CheckCircle size={13} style={{ color: "var(--low-fg)", flexShrink: 0 }} aria-hidden />
                  <span style={{ fontSize: 12.5, color: "var(--low-fg)", fontWeight: 500 }}>
                    Validated autofix available
                  </span>
                  {autofix.confidence != null && (
                    <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)", marginLeft: "auto" }}>
                      {Math.round(autofix.confidence * 100)}% confidence
                    </span>
                  )}
                </div>
                <div className="evidence-block">
                  <div className="evidence-header"><span>PATCH</span></div>
                  <pre className="evidence-code">{autofix.patch}</pre>
                </div>
                {autofix.validation_note && (
                  <p style={{ fontSize: 12, color: "var(--fg-4)", margin: 0 }}>{autofix.validation_note}</p>
                )}
                {latestFinding.run_id && (
                  <Link
                    to={`/runs/${latestFinding.run_id}`}
                    className="btn-ghost"
                    style={{ alignSelf: "flex-start", height: 30, fontSize: 12, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6 }}
                  >
                    <ExternalLink size={12} aria-hidden /> Open full run for autofix PR
                  </Link>
                )}
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <p style={{ fontSize: 13, color: "var(--fg-4)", margin: 0 }}>
                  No validated autofix available for this vulnerability.
                </p>
                {latestFinding.run_id && (
                  <Link
                    to={`/runs/${latestFinding.run_id}`}
                    className="btn-ghost"
                    style={{ alignSelf: "flex-start", height: 30, fontSize: 12, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6 }}
                  >
                    <ExternalLink size={12} aria-hidden /> View run #{latestFinding.run_id}
                  </Link>
                )}
              </div>
            )}
          </section>

          {/* ── ATTESTATION ─────────────────────────────────────────────── */}
          <section
            id="attestation"
            ref={(el) => { sectionRefs.current["attestation"] = el; }}
            className="vuln-section"
          >
            <SectionTitle>Attestation Chain</SectionTitle>
            {attestation ? (
              <SectionCard>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <Shield size={14} style={{ color: "var(--emerald)" }} aria-hidden />
                    <span style={{ fontSize: 13, fontWeight: 500, color: "var(--fg-2)" }}>ECDSA-signed attestation</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)", marginLeft: "auto" }}>
                      Run #{attestation.run_id}
                    </span>
                  </div>
                  {attestation.key_id && (
                    <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>
                      Key ID: {attestation.key_id}
                    </div>
                  )}
                  <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)" }}>
                    Algorithms: {attestation.signature_algorithms?.join(", ") ?? "—"}
                  </div>
                  <p style={{ fontSize: 12, color: "var(--fg-5)", margin: 0 }}>
                    This signature covers the scan that produced this vulnerability's latest detection.
                    Verify with: <code style={{ fontFamily: "var(--mono)" }}>openssl dgst -sha256 -verify</code>
                  </p>
                </div>
              </SectionCard>
            ) : (
              <p style={{ fontSize: 13, color: "var(--fg-5)" }}>
                No attestation found for the latest scan of this vulnerability.
              </p>
            )}
          </section>

          {/* ── REFERENCES ──────────────────────────────────────────────── */}
          <section
            id="references"
            ref={(el) => { sectionRefs.current["references"] = el; }}
            className="vuln-section"
            style={{ paddingBottom: 80 }}
          >
            <SectionTitle>CVE / CWE References</SectionTitle>
            {refs.length > 0 ? (
              <div className="ref-cards">
                {refs.map((r) => (
                  <a key={r.url} href={r.url} target="_blank" rel="noopener noreferrer" className="ref-card">
                    <ExternalLink size={11} aria-hidden />
                    {r.label}
                  </a>
                ))}
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <p style={{ fontSize: 13, color: "var(--fg-5)", margin: 0 }}>
                  No mapped references for <code style={{ fontFamily: "var(--mono)" }}>{vuln.canonical_rule_id}</code>.
                </p>
                <div className="ref-cards">
                  <a
                    href={`https://cwe.mitre.org/find/index.html`}
                    target="_blank" rel="noopener noreferrer"
                    className="ref-card"
                  >
                    <ExternalLink size={11} aria-hidden /> Search CWE
                  </a>
                  <a
                    href={`https://nvd.nist.gov/vuln/search`}
                    target="_blank" rel="noopener noreferrer"
                    className="ref-card"
                  >
                    <ExternalLink size={11} aria-hidden /> Search NVD
                  </a>
                </div>
              </div>
            )}
          </section>

        </div>
      </div>
    </>
  );
}
