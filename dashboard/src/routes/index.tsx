import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRuns, useSubmitScan } from "@/lib/queries";
import { ScanCard } from "@/components/scans/ScanCard";
import { TrendChart } from "@/components/scans/TrendChart";
import { ScanProgress } from "@/components/scans/ScanProgress";
import { Dialog } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toast";
import { CountUp } from "@/components/ui/CountUp";
import { Sparkline } from "@/components/ui/Sparkline";
import { StatusBar } from "@/components/ui/StatusBar";
import { Play, RefreshCw, CheckCircle2, BookOpen } from "lucide-react";
import { submitIacScan, submitScaScan, submitSecretsScan, postAIDetection } from "@/lib/api";

export function ScansPage() {
  const { data, isLoading, refetch } = useRuns(30);
  const submitMutation = useSubmitScan();
  const navigate = useNavigate();

  const [showScanDialog, setShowScanDialog] = useState(false);
  const [targetDir, setTargetDir] = useState("");
  const [repoName, setRepoName] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [scanMode, setScanMode] = useState<"full" | "iac" | "sca" | "secrets" | "ai-detect">("full");
  const [aiResult, setAiResult] = useState<{ flagged: number; total: number; pct: number } | null>(null);

  async function handleScan(e: React.FormEvent) {
    e.preventDefault();
    setAiResult(null);
    try {
      if (scanMode === "ai-detect") {
        const res = await postAIDetection(targetDir);
        setAiResult({ flagged: res.flagged_files, total: res.total_files, pct: res.flagged_percentage });
        toast(`AI Detection: ${res.flagged_files}/${res.total_files} files flagged`, "success");
        return;
      }
      let job;
      if (scanMode === "iac") job = await submitIacScan(targetDir, repoName);
      else if (scanMode === "sca") job = await submitScaScan(targetDir, repoName);
      else if (scanMode === "secrets") job = await submitSecretsScan(targetDir, repoName);
      else job = await submitMutation.mutateAsync({ dir: targetDir, repo: repoName });
      setActiveJobId(job.job_id);
      toast("Scan started!", "success");
    } catch {
      toast("Failed to start scan", "error");
    }
  }

  function handleScanComplete(runId?: number) {
    setActiveJobId(null);
    setShowScanDialog(false);
    refetch();
    if (runId) navigate(`/runs/${runId}`);
  }

  const runs = data?.runs ?? [];
  const completedRuns = runs.filter((r) => r.status === "completed");
  const last7 = completedRuns.slice(0, 7).reverse();
  const stats = {
    total: runs.length,
    completed: completedRuns.length,
    totalFindings: runs.reduce((s, r) => s + r.total_findings, 0),
    highCount: runs.reduce((s, r) => s + r.high_count, 0),
  };
  const sparkHigh  = last7.map((r) => r.high_count);
  const sparkTotal = last7.map((r) => r.total_findings);
  const showOnboard = runs.length === 0;

  return (
    <>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Scans Dashboard</span>
        </div>
        <div className="grow" />
        <button className="btn-icon" aria-label="Refresh scan list" onClick={() => refetch()}>
          <RefreshCw size={14} aria-hidden />
        </button>
        <button className="btn-prim" aria-label="Start a new scan" onClick={() => setShowScanDialog(true)}>
          <Play size={13} aria-hidden />
          New Scan
        </button>
      </div>

      <div className="page-pad">
        <h1 className="title">Scans Dashboard</h1>
        <p className="subtitle">Recent analysis runs and security findings</p>

        {/* Onboarding */}
        {showOnboard && (
          <div className="onboard-card">
            <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--gradient)", display: "grid", placeItems: "center", flexShrink: 0 }}>
              <BookOpen size={18} style={{ color: "#fff" }} aria-hidden />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fg)", marginBottom: 6 }}>Welcome to ACR-QA</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {[
                  { step: "Start your first scan", done: false },
                  { step: "Configure .acrqa.yml policy", done: false },
                  { step: "Invite team members", done: false },
                ].map(({ step, done }) => (
                  <div key={step} className={`onboard-step${done ? " done" : ""}`}>
                    <div className={`onboard-check${done ? " done" : ""}`}>
                      {done && <CheckCircle2 size={10} aria-hidden />}
                    </div>
                    {step}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="stats">
          <div className="stat">
            <div className="lbl">Total Scans</div>
            <div className="num"><CountUp value={stats.total} /></div>
            <div className="stat-foot">
              <span className="delta">{stats.completed} completed</span>
              {sparkTotal.length > 1 && <Sparkline data={sparkTotal} color="var(--purple)" />}
            </div>
          </div>
          <div className="stat">
            <div className="lbl">Completed</div>
            <div className="num"><CountUp value={stats.completed} /></div>
            <div className="stat-foot">
              <span className="delta">{runs.length > 0 ? Math.round((stats.completed / runs.length) * 100) : 0}% success rate</span>
            </div>
          </div>
          <div className="stat">
            <div className="lbl">Total Findings</div>
            <div className="num"><CountUp value={stats.totalFindings} /></div>
            <div className="stat-foot">
              <span className="delta">all runs</span>
              {sparkTotal.length > 1 && <Sparkline data={sparkTotal} color="var(--blue)" />}
            </div>
          </div>
          <div className="stat">
            <div className="lbl">HIGH Severity</div>
            <div className={`num${stats.highCount > 0 ? " danger" : ""}`}><CountUp value={stats.highCount} /></div>
            <div className="stat-foot">
              <span className="delta">needs attention</span>
              {sparkHigh.length > 1 && <Sparkline data={sparkHigh} color="var(--high)" />}
            </div>
          </div>
        </div>

        {/* Trend chart */}
        <div className="panel" style={{ marginBottom: 24 }}>
          <div className="panel-head">
            <span className="panel-title">Findings Trend</span>
          </div>
          <TrendChart />
        </div>

        {/* Scan list */}
        <div className="findings-head">
          <h3>
            Recent Scans
            {runs.length > 0 && <span className="n">{runs.length}</span>}
          </h3>
        </div>

        {isLoading ? (
          <div className="empty">
            <span className="spinner" />
            Loading scans…
          </div>
        ) : runs.length === 0 ? (
          <div className="empty">
            <p>No scans yet.</p>
            <button className="btn-prim" onClick={() => setShowScanDialog(true)}>
              <Play size={13} aria-hidden /> Run your first scan
            </button>
          </div>
        ) : (
          <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))" }}>
            {runs.map((r) => <ScanCard key={r.id} run={r} />)}
          </div>
        )}
      </div>

      <StatusBar items={[
        { label: "Scans", value: stats.total },
        { label: "Findings", value: stats.totalFindings },
        { label: "HIGH", value: stats.highCount, color: stats.highCount > 0 ? "var(--high)" : "var(--low)" },
      ]} />

      {/* New scan dialog */}
      <Dialog open={showScanDialog} onClose={() => setShowScanDialog(false)} title="New Scan">
        <form onSubmit={handleScan} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="field">
            <label>Target directory</label>
            <input className="inp" value={targetDir} onChange={(e) => setTargetDir(e.target.value)} placeholder="/path/to/repo" required />
          </div>
          {scanMode !== "ai-detect" && (
            <div className="field">
              <label>Repo name</label>
              <input className="inp" value={repoName} onChange={(e) => setRepoName(e.target.value)} placeholder="my-service" required />
            </div>
          )}
          <div className="field">
            <label>Scan type</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 4 }}>
              {([
                { mode: "full", title: "Full Scan", desc: "SAST + AI + all engines" },
                { mode: "iac", title: "IaC Scanner", desc: "Terraform, K8s, Dockerfile" },
                { mode: "sca", title: "SCA (Dependencies)", desc: "Known CVEs in deps" },
                { mode: "secrets", title: "Secrets Detector", desc: "API keys, tokens, passwords" },
                { mode: "ai-detect", title: "AI Code Detector", desc: "Detect LLM-generated code" },
              ] as const).map(({ mode, title, desc }) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => { setScanMode(mode); setAiResult(null); }}
                  style={{
                    borderRadius: 8,
                    padding: "10px 12px",
                    textAlign: "left",
                    background: scanMode === mode ? "var(--ai-bg)" : "transparent",
                    border: `1px solid ${scanMode === mode ? "var(--ai-bdr)" : "var(--border-2)"}`,
                    cursor: "pointer",
                    transition: "background 0.15s",
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--fg)", marginBottom: 2 }}>{title}</div>
                  <div style={{ fontSize: 11.5, color: "var(--fg-4)" }}>{desc}</div>
                </button>
              ))}
            </div>
          </div>
          {aiResult && (
            <div style={{ background: "rgba(16,185,129,0.08)", border: "1px solid var(--low-bdr)", borderRadius: 8, padding: "12px 14px" }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--low-fg)", marginBottom: 4 }}>AI Detection Results</div>
              <div style={{ fontSize: 12.5, color: "var(--fg-3)" }}>
                {aiResult.flagged} / {aiResult.total} files flagged ({aiResult.pct.toFixed(1)}% likely AI-generated)
              </div>
            </div>
          )}
          {activeJobId && (
            <div style={{ border: "1px solid var(--border-2)", borderRadius: 8, padding: 12 }}>
              <ScanProgress jobId={activeJobId} onComplete={handleScanComplete} />
            </div>
          )}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button type="button" className="btn-ghost" onClick={() => setShowScanDialog(false)}>Cancel</button>
            <button type="submit" className="btn-prim" disabled={submitMutation.isPending || !!activeJobId}>
              {submitMutation.isPending ? <span className="spinner" style={{ width: 14, height: 14 }} /> : <Play size={13} aria-hidden />}
              Start Scan
            </button>
          </div>
        </form>
      </Dialog>
    </>
  );
}
