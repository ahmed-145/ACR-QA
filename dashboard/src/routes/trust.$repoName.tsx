/**
 * Public Trust Page — /trust/:repoName
 *
 * No authentication required. Shows aggregate security posture only —
 * no file paths, rule IDs, or specific vulnerability details are revealed.
 *
 * Implements 6.4: in-browser ECDSA-P256 verification via WebCrypto API.
 * Implements 6.7: signature embedded in <meta> tag in document head.
 */

import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useTrustPosture, useTrustAttestation, useTrustPublicKey } from "@/lib/queries";
import type { TrustCompliance } from "@/lib/api";
import {
  Shield, CheckCircle, XCircle, AlertTriangle,
  Clock, Activity, Link2, Download, ExternalLink, RefreshCw,
} from "lucide-react";

// ── WebCrypto in-browser ECDSA-P256 verification ──────────────────────────────

function pemToBuffer(pem: string): ArrayBuffer {
  const b64 = pem
    .replace(/-----BEGIN PUBLIC KEY-----/, "")
    .replace(/-----END PUBLIC KEY-----/, "")
    .replace(/\s+/g, "");
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

function hexToBuffer(hex: string): ArrayBuffer {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return bytes.buffer;
}

// Deep-sort JSON keys for canonical serialization matching Python's json.dumps(sort_keys=True)
function sortedJsonBytes(obj: unknown): Uint8Array {
  function sortKeys(v: unknown): unknown {
    if (Array.isArray(v)) return v.map(sortKeys);
    if (v !== null && typeof v === "object") {
      const sorted: Record<string, unknown> = {};
      for (const k of Object.keys(v as object).sort()) sorted[k] = sortKeys((v as Record<string, unknown>)[k]);
      return sorted;
    }
    return v;
  }
  return new TextEncoder().encode(JSON.stringify(sortKeys(obj), null, 0).replace(/,\s*/g, ",").replace(/:\s*/g, ":"));
}

type VerifyState = "idle" | "verifying" | "valid" | "invalid" | "unavailable";

async function verifyPosture(
  posture: Record<string, unknown>,
  sigHex: string,
  pubKeyPem: string,
): Promise<boolean> {
  const keyBuf = pemToBuffer(pubKeyPem);
  const cryptoKey = await window.crypto.subtle.importKey(
    "spki",
    keyBuf,
    { name: "ECDSA", namedCurve: "P-256" },
    false,
    ["verify"],
  );

  // Strip the 'signature', 'public_key_url', 'attestation_url' fields before hashing
  // to match what the server signs (the posture dict without those fields)
  const { signature: _sig, public_key_url: _pku, attestation_url: _atu, ...postureCopy } = posture;
  void _sig; void _pku; void _atu;

  const payload = sortedJsonBytes(postureCopy);
  const sigBuf  = hexToBuffer(sigHex);

  return window.crypto.subtle.verify(
    { name: "ECDSA", hash: "SHA-256" },
    cryptoKey,
    sigBuf,
    payload,
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

const STATUS_COLORS = {
  pass: "var(--sev-low)",
  warn: "var(--sev-medium)",
  fail: "var(--sev-high)",
};

const STATUS_ICONS = {
  pass: <CheckCircle size={14} aria-hidden />,
  warn: <AlertTriangle size={14} aria-hidden />,
  fail: <XCircle size={14} aria-hidden />,
};

function ComplianceRow({ label, status }: { label: string; status: keyof TrustCompliance | "pass" | "warn" | "fail" }) {
  const s = status as "pass" | "warn" | "fail";
  return (
    <div className="trust-compliance-row">
      <span className="trust-compliance-label">{label}</span>
      <span className="trust-compliance-status" style={{ color: STATUS_COLORS[s] }}>
        {STATUS_ICONS[s]}
        <span>{s.toUpperCase()}</span>
      </span>
    </div>
  );
}

function VerifyBadge({ state }: { state: VerifyState }) {
  if (state === "idle") return null;
  const map: Record<VerifyState, { icon: React.ReactNode; text: string; color: string }> = {
    idle:        { icon: null, text: "", color: "" },
    verifying:   { icon: <RefreshCw size={12} aria-hidden style={{ animation: "spin 1s linear infinite" }} />, text: "Verifying…",  color: "var(--fg-4)" },
    valid:       { icon: <CheckCircle size={12} aria-hidden />, text: "Signature valid — verified in browser",   color: "var(--sev-low)" },
    invalid:     { icon: <XCircle size={12} aria-hidden />,     text: "Signature INVALID — payload may be tampered", color: "var(--sev-high)" },
    unavailable: { icon: <AlertTriangle size={12} aria-hidden />, text: "No signature — server in ephemeral key mode", color: "var(--sev-medium)" },
  };
  const { icon, text, color } = map[state];
  return (
    <div className="trust-verify-badge" style={{ color }} role="status" aria-live="polite">
      {icon}
      <span style={{ fontSize: 12, marginLeft: 5 }}>{text}</span>
    </div>
  );
}

function FreshnessIndicator({ days }: { days: number | null }) {
  if (days === null) return <span style={{ color: "var(--fg-5)" }}>—</span>;
  const color = days <= 7 ? "var(--sev-low)" : days <= 30 ? "var(--sev-medium)" : "var(--sev-high)";
  const label = days === 0 ? "today" : days === 1 ? "yesterday" : `${days}d ago`;
  return <span style={{ color, fontFamily: "var(--mono)", fontSize: 13 }}>{label}</span>;
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function TrustPage() {
  const { repoName } = useParams<{ repoName: string }>();
  const repo = repoName ?? "";

  const { data: posture, isLoading, isError } = useTrustPosture(repo);
  const { data: attestation } = useTrustAttestation(repo);
  const { data: pubKey } = useTrustPublicKey(repo);

  const [verifyState, setVerifyState] = useState<VerifyState>("idle");
  const [showRawAttestation, setShowRawAttestation] = useState(false);

  // Inject signature into <meta> tag (6.7)
  useEffect(() => {
    if (!posture?.signature) return;
    let meta = document.querySelector<HTMLMetaElement>("meta[name='x-acrqa-sig']");
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "x-acrqa-sig";
      document.head.appendChild(meta);
    }
    meta.content = posture.signature.signature;
    return () => meta?.remove();
  }, [posture?.signature]);

  const handleVerify = async () => {
    if (!posture) return;
    if (!posture.signature) { setVerifyState("unavailable"); return; }
    if (!pubKey?.pem) { setVerifyState("unavailable"); return; }

    setVerifyState("verifying");
    try {
      const valid = await verifyPosture(
        posture as unknown as Record<string, unknown>,
        posture.signature.signature,
        pubKey.pem,
      );
      setVerifyState(valid ? "valid" : "invalid");
    } catch {
      setVerifyState("invalid");
    }
  };

  const overall = posture?.compliance.overall ?? "fail";
  const overallColor = STATUS_COLORS[overall];

  return (
    <div className="trust-page" data-repo={repo}>
      {/* Public header — no sidebar */}
      <header className="trust-header">
        <div className="trust-header-inner">
          <div className="trust-brand">
            <span className="logo" aria-hidden>✦</span>
            <span className="trust-brand-name">ACR-QA</span>
            <span className="trust-brand-sep">/</span>
            <span className="trust-brand-type">Security Posture</span>
          </div>
          <Link to="/" className="trust-back-link" style={{ textDecoration: "none", fontSize: 12, color: "var(--fg-5)" }}>
            ← Dashboard
          </Link>
        </div>
      </header>

      <main className="trust-main" role="main">
        {isLoading && (
          <div className="trust-loading">
            <span className="spinner" style={{ width: 24, height: 24 }} aria-label="Loading posture data" />
          </div>
        )}

        {isError && (
          <div className="trust-error">
            <XCircle size={20} aria-hidden style={{ color: "var(--sev-high)" }} />
            <div>
              <div style={{ fontWeight: 600, color: "var(--fg)", marginBottom: 4 }}>No posture data found</div>
              <div style={{ fontSize: 13, color: "var(--fg-4)" }}>
                No completed scans found for <code className="trust-inline-code">{repo}</code>.
                Run a scan first with: <code className="trust-inline-code">python CORE/main.py --repo-name {repo} …</code>
              </div>
            </div>
          </div>
        )}

        {posture && (
          <>
            {/* Hero */}
            <div className="trust-hero">
              <div className="trust-repo-name">{posture.repo_name}</div>
              <div className="trust-overall" style={{ color: overallColor }}>
                {STATUS_ICONS[overall]}
                <span className="trust-overall-label">
                  {overall === "pass" ? "Passing" : overall === "warn" ? "Warning" : "Critical Issues"}
                </span>
              </div>
              <div className="trust-badge-row">
                <img
                  src={`/v1/trust/badge/${encodeURIComponent(repo)}`}
                  alt={`Security status for ${repo}`}
                  className="trust-live-badge"
                />
                <button
                  className="trust-copy-btn"
                  onClick={() => {
                    const md = `![security](${window.location.origin}/v1/trust/badge/${encodeURIComponent(repo)})`;
                    navigator.clipboard.writeText(md).catch(() => undefined);
                  }}
                  title="Copy Markdown badge"
                  aria-label="Copy badge markdown to clipboard"
                >
                  Copy badge
                </button>
              </div>
            </div>

            {/* Stats grid */}
            <div className="trust-grid">
              {/* Vulnerability counts */}
              <div className="trust-card trust-card-wide">
                <div className="trust-card-title">
                  <Shield size={14} aria-hidden /> Open Vulnerabilities
                </div>
                <div className="trust-vuln-grid">
                  {[
                    { label: "Critical",   value: posture.open_high, color: "var(--sev-high)" },
                    { label: "Medium",     value: posture.open_med,  color: "var(--sev-medium)" },
                    { label: "Low",        value: posture.open_low,  color: "var(--sev-low)" },
                    { label: "Fixed",      value: posture.fixed_total, color: "var(--fg-3)" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="trust-vuln-stat">
                      <div className="trust-vuln-count" style={{ color }}>{value}</div>
                      <div className="trust-vuln-label">{label}</div>
                    </div>
                  ))}
                </div>
                {posture.regressions > 0 && (
                  <div className="trust-regression-note">
                    <AlertTriangle size={11} aria-hidden /> {posture.regressions} regression{posture.regressions > 1 ? "s" : ""} — previously fixed issues reintroduced
                  </div>
                )}
              </div>

              {/* Scan activity */}
              <div className="trust-card">
                <div className="trust-card-title">
                  <Activity size={14} aria-hidden /> Scan Activity
                </div>
                <div className="trust-stat-rows">
                  <div className="trust-stat-row">
                    <span className="trust-stat-key">Last scan</span>
                    <FreshnessIndicator days={posture.freshness_days} />
                  </div>
                  <div className="trust-stat-row">
                    <span className="trust-stat-key">Total scans</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 13 }}>{posture.scan_count}</span>
                  </div>
                  {posture.scan_frequency_per_week != null && (
                    <div className="trust-stat-row">
                      <span className="trust-stat-key">Scan frequency</span>
                      <span style={{ fontFamily: "var(--mono)", fontSize: 13 }}>
                        {posture.scan_frequency_per_week.toFixed(1)}×/week
                      </span>
                    </div>
                  )}
                  {posture.freshness_days !== null && posture.freshness_days > 30 && (
                    <div className="trust-stale-note">
                      <Clock size={11} aria-hidden /> Scan is over 30 days old — posture may be outdated
                    </div>
                  )}
                </div>
              </div>

              {/* Compliance */}
              <div className="trust-card">
                <div className="trust-card-title">
                  <CheckCircle size={14} aria-hidden /> Compliance
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
                  <ComplianceRow label="OWASP Top 10"  status={posture.compliance.owasp_top10} />
                  <ComplianceRow label="CWE Top 25"    status={posture.compliance.cwe_top25} />
                  <ComplianceRow label="Overall"       status={posture.compliance.overall} />
                </div>
              </div>

              {/* Verification */}
              <div className="trust-card">
                <div className="trust-card-title">
                  <Link2 size={14} aria-hidden /> Attestation
                </div>
                <div style={{ fontSize: 12, color: "var(--fg-4)", lineHeight: 1.6, marginBottom: 12 }}>
                  This posture payload is signed with ECDSA-P256. Click to verify the signature
                  in your browser using the Web Crypto API — no server trust required.
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    className="btn-prim"
                    style={{ gap: 6, height: 32, fontSize: 12 }}
                    onClick={handleVerify}
                    disabled={verifyState === "verifying"}
                    aria-label="Verify ECDSA signature in browser"
                  >
                    <Shield size={12} aria-hidden />
                    Verify In Browser
                  </button>
                  {attestation && (
                    <button
                      className="btn-ghost"
                      style={{ gap: 6, height: 32, fontSize: 12 }}
                      onClick={() => setShowRawAttestation((v) => !v)}
                      aria-label="Toggle raw attestation bundle"
                    >
                      <ExternalLink size={12} aria-hidden />
                      {showRawAttestation ? "Hide" : "Raw Bundle"}
                    </button>
                  )}
                </div>
                <VerifyBadge state={verifyState} />
                {posture.signature && (
                  <div className="trust-sig-meta">
                    <span className="trust-sig-label">key_id</span>
                    <code className="trust-sig-value">{posture.signature.key_id}</code>
                  </div>
                )}
              </div>
            </div>

            {/* Raw attestation bundle (expandable) */}
            {showRawAttestation && attestation && (
              <div className="trust-card trust-attestation-block">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                  <span className="trust-card-title" style={{ marginBottom: 0 }}>
                    <Download size={13} aria-hidden /> Signed Attestation Bundle
                  </span>
                  <a
                    href={`/v1/trust/${encodeURIComponent(repo)}/attestation`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-ghost"
                    style={{ fontSize: 11, height: 26, gap: 4, textDecoration: "none" }}
                  >
                    <ExternalLink size={11} aria-hidden /> Open raw JSON
                  </a>
                </div>
                <pre className="trust-bundle-pre">
                  {JSON.stringify(attestation.bundle, null, 2)}
                </pre>
                {attestation.signature && (
                  <div style={{ marginTop: 10 }}>
                    <div className="trust-sig-meta">
                      <span className="trust-sig-label">signature (hex)</span>
                      <code className="trust-sig-value" style={{ wordBreak: "break-all" }}>
                        {attestation.signature.slice(0, 64)}…
                      </code>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Footer */}
            <div className="trust-footer">
              <span>Generated {new Date(posture.generated_at).toLocaleString()} UTC</span>
              <span className="trust-footer-sep">·</span>
              <a href={`/v1/trust/${encodeURIComponent(repo)}/public-key`}
                 target="_blank" rel="noopener noreferrer" className="trust-footer-link">
                Public key
              </a>
              <span className="trust-footer-sep">·</span>
              <a href={`/v1/trust/badge/${encodeURIComponent(repo)}`}
                 target="_blank" rel="noopener noreferrer" className="trust-footer-link">
                SVG badge
              </a>
              <span className="trust-footer-sep">·</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 10.5 }}>ACR-QA v5.0.0-b1</span>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
