import { useState, useEffect, useRef } from "react";
import { type Finding, postSecondOpinion, type SecondOpinion } from "@/lib/api";
import { TaintFlowGraph } from "./TaintFlowGraph";
import { ReasoningChain } from "./ReasoningChain";
import { AutofixDiff } from "./AutofixDiff";
import { ExploitProofPanel } from "./ExploitProofPanel";
import { ChatSidebar } from "./ChatSidebar";
import { CallGraph } from "./CallGraph";
import { FindingHistory } from "./FindingHistory";
import { X } from "lucide-react";

interface Props {
  finding: Finding | null;
  runId: number;
  onClose: () => void;
}

const TABS = ["Overview", "2nd Opinion", "Autofix", "Taint", "Exploit", "Reasoning", "Chat", "Call Graph", "History"] as const;
type ModalTab = typeof TABS[number];

export function FindingModal({ finding, runId, onClose }: Props) {
  const [tab, setTab] = useState<ModalTab>("Overview");
  const [opinion, setOpinion] = useState<SecondOpinion | null>(null);
  const [opinionLoading, setOpinionLoading] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!finding) return;
    setTab("Overview");
    setOpinion(null);
  }, [finding?.id]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function fetchOpinion() {
    if (!finding) return;
    setOpinionLoading(true);
    try {
      setOpinion(await postSecondOpinion(finding.id));
    } finally {
      setOpinionLoading(false);
    }
  }

  if (!finding) return null;

  const sev = finding.severity.toUpperCase();
  const sevCls = sev === "HIGH" ? "high" : sev === "MEDIUM" ? "med" : "low";

  return (
    <div
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      style={{
        position: "fixed", inset: 0, zIndex: 100,
        background: "rgba(0,0,0,0.72)", backdropFilter: "blur(6px)",
        display: "flex", alignItems: "flex-start", justifyContent: "center",
        padding: "40px 24px", overflowY: "auto",
      }}
    >
      <div className="modal-card" style={{
        width: "100%", maxWidth: 860,
        display: "flex", flexDirection: "column", minHeight: 0,
      }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "flex-start", gap: 12,
          padding: "18px 20px 14px",
          borderBottom: "1px solid var(--border)",
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
              <span className={`sev ${sevCls}`}>{sev}</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: 13, color: "var(--fg)", fontWeight: 600 }}>
                {finding.rule_id}
              </span>
              {finding.category && (
                <span style={{
                  fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)",
                  padding: "1px 7px", borderRadius: 4, background: "rgba(255,255,255,0.04)",
                  border: "1px solid var(--border-2)",
                }}>{finding.category}</span>
              )}
              {finding.tool && (
                <span style={{ fontSize: 11, color: "var(--fg-5)" }}>via {finding.tool}</span>
              )}
              <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)" }}>CONF</span>
                <div style={{ width: 48, height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 999, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${Math.round((finding.confidence ?? 0) * 100)}%`, background: "var(--gradient)", borderRadius: 999 }} />
                </div>
                <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-3)", fontWeight: 600 }}>
                  {Math.round((finding.confidence ?? 0) * 100)}%
                </span>
              </span>
            </div>
            <div style={{
              fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-4)",
              padding: "4px 8px", background: "var(--bg-3)", borderRadius: 5,
              border: "1px solid var(--border)", display: "inline-block",
            }}>
              {finding.file_path}{finding.line_number ? `:${finding.line_number}` : ""}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none", color: "var(--fg-4)",
              cursor: "pointer", padding: 4, borderRadius: 6, flexShrink: 0,
              display: "flex", alignItems: "center",
            }}
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div style={{ borderBottom: "1px solid var(--border)", padding: "0 20px", overflowX: "auto" }}>
          <div className="tabs" style={{ margin: 0, borderBottom: "none", gap: 0 }}>
            {TABS.map((t) => (
              <button
                key={t}
                className={`tab${tab === t ? " on" : ""}`}
                onClick={() => setTab(t)}
                style={{ fontSize: 12 }}
              >{t}</button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: "20px", overflowY: "auto", maxHeight: "calc(90vh - 200px)" }}>
          {tab === "Overview" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: "var(--fg-5)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>Message</div>
                <p style={{ fontSize: 13.5, color: "var(--fg-2)", lineHeight: 1.7, margin: 0 }}>{finding.message}</p>
              </div>
              {finding.explanation_text && (
                <div className="ai-block" style={{ margin: 0 }}>
                  <div style={{ fontSize: 11, color: "var(--purple)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                    AI Explanation · {finding.model_name ?? "LLM"}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--fg-2)", lineHeight: 1.75, whiteSpace: "pre-wrap" }}>
                    {finding.explanation_text}
                  </div>
                </div>
              )}
              {finding.triage_verdict && (
                <div style={{
                  padding: "10px 14px", borderRadius: 7,
                  background: finding.triage_verdict === "TP" ? "rgba(239,68,68,0.08)" : "rgba(16,185,129,0.08)",
                  border: `1px solid ${finding.triage_verdict === "TP" ? "rgba(239,68,68,0.25)" : "rgba(16,185,129,0.25)"}`,
                }}>
                  <span style={{ fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700, color: finding.triage_verdict === "TP" ? "var(--high-fg)" : "var(--low-fg)" }}>
                    Triage: {finding.triage_verdict}
                  </span>
                  {finding.triage_reasoning && (
                    <p style={{ fontSize: 12, color: "var(--fg-3)", margin: "6px 0 0" }}>{finding.triage_reasoning}</p>
                  )}
                </div>
              )}
              {finding.exploit_tier && (
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span className={`conf ${finding.exploit_tier === "critical" ? "high" : finding.exploit_tier === "medium" ? "med" : "low"}`}>
                    Exploit: {finding.exploit_tier}
                  </span>
                  {finding.exploit_duration_seconds && (
                    <span style={{ fontSize: 11, color: "var(--fg-5)" }}>{finding.exploit_duration_seconds}s</span>
                  )}
                </div>
              )}
            </div>
          )}

          {tab === "2nd Opinion" && (
            <div>
              {!opinion && !opinionLoading && (
                <div style={{ textAlign: "center", padding: "40px 0" }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>🤖</div>
                  <p style={{ fontSize: 13, color: "var(--fg-4)", marginBottom: 20 }}>
                    Cross-check this finding with a second AI provider.
                  </p>
                  <button className="btn-prim" onClick={fetchOpinion}>
                    Request Second Opinion
                  </button>
                </div>
              )}
              {opinionLoading && (
                <div style={{ textAlign: "center", padding: "40px 0", color: "var(--fg-4)" }}>
                  <span className="spinner" style={{ marginRight: 8 }} />
                  Consulting second model…
                </div>
              )}
              {opinion && (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{
                    padding: "12px 16px", borderRadius: 8,
                    background: opinion.agreement ? "rgba(16,185,129,0.08)" : "rgba(245,158,11,0.08)",
                    border: `1px solid ${opinion.agreement ? "rgba(16,185,129,0.25)" : "rgba(245,158,11,0.25)"}`,
                    fontSize: 13, fontWeight: 600,
                    color: opinion.agreement ? "var(--low-fg)" : "var(--med-fg)",
                  }}>
                    {opinion.agreement ? "✓ Models agree" : "⚠ Models disagree — manual review recommended"}
                  </div>
                  {[
                    { provider: opinion.primary_provider, verdict: opinion.primary_verdict, reason: opinion.primary_reason },
                    { provider: opinion.secondary_provider, verdict: opinion.secondary_verdict, reason: opinion.secondary_reason },
                  ].map(({ provider, verdict, reason }) => (
                    <div key={provider} style={{
                      borderRadius: 8, border: "1px solid var(--border-2)",
                      background: "var(--bg-3)", padding: "12px 16px",
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-3)", padding: "2px 7px", background: "rgba(255,255,255,0.04)", borderRadius: 4 }}>{provider}</span>
                        <span className={`sev ${verdict === "TP" ? "high" : verdict === "FP" ? "low" : "med"}`}>{verdict}</span>
                      </div>
                      {reason && <p style={{ fontSize: 12.5, color: "var(--fg-3)", margin: 0, lineHeight: 1.6 }}>{reason}</p>}
                    </div>
                  ))}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--fg-5)" }}>
                      Latency: {opinion.latency_ms}ms
                    </span>
                    <button className="btn-ghost" onClick={fetchOpinion} disabled={opinionLoading}>Re-run</button>
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === "Autofix" && <AutofixDiff runId={runId} findingId={finding.id} />}
          {tab === "Taint" && <TaintFlowGraph finding={finding} />}
          {tab === "Exploit" && <ExploitProofPanel finding={finding} />}
          {tab === "Reasoning" && <ReasoningChain finding={finding} />}
          {tab === "Chat" && <ChatSidebar findingId={finding.id} />}
          {tab === "Call Graph" && <CallGraph findingId={finding.id} />}
          {tab === "History" && <FindingHistory findingId={finding.id} />}
        </div>
      </div>
    </div>
  );
}
