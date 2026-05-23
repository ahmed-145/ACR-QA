import { useState } from "react";
import { useAIDetection } from "@/lib/queries";
import { toast } from "@/components/ui/toast";
import { Brain, FolderOpen, AlertTriangle, CheckCircle } from "lucide-react";

export function AIDetectPage() {
  const [targetDir, setTargetDir] = useState("");
  const [threshold, setThreshold] = useState(0.6);
  const detect = useAIDetection();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!targetDir.trim()) return;
    try {
      await detect.mutateAsync({ target: targetDir.trim(), threshold });
      toast("Detection complete", "success");
    } catch {
      toast("Detection failed — check the target path", "error");
    }
  }

  const result = detect.data;
  const flaggedPct = result ? result.flagged_percentage : 0;
  const riskLevel = flaggedPct >= 50 ? "high" : flaggedPct >= 20 ? "med" : "low";

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">AI Code Detector</span>
        </div>
      </div>

      <div className="page-pad" style={{ maxWidth: 860 }}>
        <h1 className="title">AI Code Detector</h1>
        <p className="subtitle">Detect LLM-generated code in your codebase using heuristic analysis</p>

        {/* Input form */}
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-head">
            <span className="panel-title">Target</span>
          </div>
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="field">
              <label htmlFor="ai-target">Directory path</label>
              <div style={{ display: "flex", gap: 8 }}>
                <FolderOpen size={14} style={{ color: "var(--fg-4)", alignSelf: "center", flexShrink: 0 }} aria-hidden />
                <input
                  id="ai-target"
                  className="inp"
                  value={targetDir}
                  onChange={(e) => setTargetDir(e.target.value)}
                  placeholder="/path/to/your/repo"
                  required
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="ai-threshold">
                Confidence threshold: <span style={{ fontFamily: "var(--mono)", color: "var(--purple)" }}>{threshold.toFixed(2)}</span>
              </label>
              <input
                id="ai-threshold"
                type="range"
                min={0.1}
                max={0.95}
                step={0.05}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--purple)" }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10.5, fontFamily: "var(--mono)", color: "var(--fg-5)", marginTop: 2 }}>
                <span>0.10 (sensitive)</span>
                <span>0.95 (conservative)</span>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="submit"
                className="btn-prim"
                disabled={detect.isPending || !targetDir.trim()}
              >
                {detect.isPending ? (
                  <><span className="spinner" style={{ width: 14, height: 14 }} aria-hidden /> Scanning…</>
                ) : (
                  <><Brain size={13} aria-hidden /> Run Detection</>
                )}
              </button>
              {result && (
                <button type="button" className="btn-ghost" onClick={() => detect.reset()}>Clear</button>
              )}
            </div>
          </form>
        </div>

        {/* Results */}
        {result && (
          <>
            {/* Summary stats */}
            <div className="stats" style={{ marginBottom: 16 }}>
              <div className="stat">
                <div className="lbl">Files Scanned</div>
                <div className="num">{result.total_files}</div>
              </div>
              <div className={`stat${result.flagged_files > 0 ? "" : ""}`}>
                <div className="lbl">Flagged Files</div>
                <div className={`num${result.flagged_files > 0 ? " danger" : ""}`}>{result.flagged_files}</div>
              </div>
              <div className="stat precision">
                <div className="lbl">AI-generated %</div>
                <div className="num">{result.flagged_percentage.toFixed(1)}<small>%</small></div>
              </div>
              <div className="stat">
                <div className="lbl">Risk Level</div>
                <div style={{ marginTop: 8 }}>
                  <span className={`sev ${riskLevel}`} style={{ fontSize: 14 }}>
                    {riskLevel === "high" ? "HIGH" : riskLevel === "med" ? "MEDIUM" : "LOW"}
                  </span>
                </div>
              </div>
            </div>

            {/* Verdict banner */}
            <div
              className="panel"
              style={{
                marginBottom: 16,
                background: result.flagged_files === 0
                  ? "rgba(16,185,129,0.08)"
                  : riskLevel === "high" ? "rgba(239,68,68,0.08)" : "rgba(245,158,11,0.08)",
                border: `1px solid ${result.flagged_files === 0 ? "var(--low-bdr)" : riskLevel === "high" ? "var(--high-bdr)" : "var(--med-bdr)"}`,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                {result.flagged_files === 0
                  ? <CheckCircle size={20} style={{ color: "var(--low)", flexShrink: 0 }} aria-hidden />
                  : <AlertTriangle size={20} style={{ color: riskLevel === "high" ? "var(--high)" : "var(--med)", flexShrink: 0 }} aria-hidden />
                }
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fg)", marginBottom: 4 }}>
                    {result.flagged_files === 0
                      ? "No AI-generated code detected"
                      : `${result.flagged_files} file${result.flagged_files > 1 ? "s" : ""} likely contain AI-generated code`}
                  </div>
                  <div style={{ fontSize: 12.5, color: "var(--fg-4)" }}>
                    {result.flagged_files === 0
                      ? "All scanned files appear to be human-authored."
                      : `${result.flagged_percentage.toFixed(1)}% of your codebase matches AI generation patterns at threshold ${threshold.toFixed(2)}.`}
                  </div>
                </div>
              </div>
            </div>

            {/* Flagged file list */}
            {result.flagged_files > 0 && result.files && result.files.length > 0 && (
              <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
                <div className="panel-head" style={{ padding: "14px 18px 12px" }}>
                  <span className="panel-title">Flagged Files</span>
                  <span className="panel-sub">{result.files.length} files</span>
                </div>
                <div style={{ borderTop: "1px solid var(--border)", maxHeight: 400, overflowY: "auto" }}>
                  {result.files.map((f: { file_path: string; score: number }) => (
                    <div key={f.file_path} style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "center", gap: 12, padding: "10px 18px", borderBottom: "1px solid var(--border)" }}>
                      <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--fg-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {f.file_path}
                      </span>
                      <span className={`conf ${f.score >= 0.7 ? "hi" : f.score >= 0.4 ? "md" : "lo"}`}>
                        {Math.round(f.score * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Info box when no result yet */}
        {!result && !detect.isPending && (
          <div className="panel" style={{ background: "var(--ai-bg)", border: "1px solid var(--ai-bdr)" }}>
            <div className="ai-head" style={{ marginBottom: 12 }}>
              <span className="ai-kicker">How it works</span>
            </div>
            <p className="ai-text" style={{ margin: 0 }}>
              The detector analyzes source files for statistical patterns common in LLM-generated code:
              repetitive structure, uniform comment density, unusually consistent naming conventions, and
              entropy signatures. Files scoring above the threshold are flagged for human review.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
