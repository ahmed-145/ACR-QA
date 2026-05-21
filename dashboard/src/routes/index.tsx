import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRuns, useSubmitScan } from "@/lib/queries";
import { ScanCard } from "@/components/scans/ScanCard";
import { TrendChart } from "@/components/scans/TrendChart";
import { ScanProgress } from "@/components/scans/ScanProgress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toast";
import { Loader2, Play, RefreshCw, TrendingUp } from "lucide-react";
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
  const stats = {
    total: runs.length,
    completed: runs.filter((r) => r.status === "completed").length,
    totalFindings: runs.reduce((s, r) => s + r.total_findings, 0),
    highCount: runs.reduce((s, r) => s + r.high_count, 0),
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Scans Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">Recent analysis runs and security findings</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" aria-label="Refresh scan list" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-1" aria-hidden /> Refresh
          </Button>
          <Button size="sm" aria-label="Start a new scan" onClick={() => setShowScanDialog(true)}>
            <Play className="h-4 w-4 mr-1" aria-hidden /> New Scan
          </Button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Total Scans", value: stats.total },
          { label: "Completed", value: stats.completed },
          { label: "Total Findings", value: stats.totalFindings },
          { label: "HIGH Severity", value: stats.highCount, danger: stats.highCount > 0 },
        ].map(({ label, value, danger }) => (
          <Card key={label}>
            <CardContent className="pt-4">
              <div className={`text-2xl font-bold ${danger ? "text-red-600" : ""}`}>{value}</div>
              <div className="text-xs text-muted-foreground mt-1">{label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Trend chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> Findings Trend
          </CardTitle>
        </CardHeader>
        <CardContent>
          <TrendChart />
        </CardContent>
      </Card>

      {/* Scan list */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Recent Scans</h2>
        {isLoading ? (
          <div className="flex items-center gap-2 text-muted-foreground py-8 justify-center">
            <Loader2 className="h-5 w-5 animate-spin" /> Loading scans…
          </div>
        ) : runs.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <p className="mb-3">No scans yet.</p>
            <Button onClick={() => setShowScanDialog(true)}>
              <Play className="h-4 w-4 mr-1" /> Run your first scan
            </Button>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {runs.map((r) => <ScanCard key={r.id} run={r} />)}
          </div>
        )}
      </div>

      {/* New scan dialog */}
      <Dialog open={showScanDialog} onClose={() => setShowScanDialog(false)} title="New Scan">
        <form onSubmit={handleScan} className="space-y-4">
          <div>
            <label className="text-sm font-medium">Target directory</label>
            <Input value={targetDir} onChange={(e) => setTargetDir(e.target.value)} placeholder="/path/to/repo" required className="mt-1" />
          </div>
          {scanMode !== "ai-detect" && (
            <div>
              <label className="text-sm font-medium">Repo name</label>
              <Input value={repoName} onChange={(e) => setRepoName(e.target.value)} placeholder="my-service" required className="mt-1" />
            </div>
          )}
          <div>
            <label className="text-sm font-medium mb-2 block">Scan type</label>
            <div className="grid grid-cols-2 gap-2">
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
                  className={`rounded-lg border px-3 py-2 text-sm text-left transition-colors ${scanMode === mode ? "border-primary bg-primary/5 font-medium" : "hover:bg-muted"}`}
                >
                  <div className="font-medium">{title}</div>
                  <div className="text-xs text-muted-foreground">{desc}</div>
                </button>
              ))}
            </div>
          </div>
          {aiResult && (
            <div className="rounded-lg border bg-muted/30 p-3 text-sm space-y-1">
              <div className="font-medium">AI Detection Results</div>
              <div className="text-muted-foreground">
                {aiResult.flagged} / {aiResult.total} files flagged ({aiResult.pct.toFixed(1)}% likely AI-generated)
              </div>
            </div>
          )}
          {activeJobId && (
            <div className="rounded-lg border p-3">
              <ScanProgress jobId={activeJobId} onComplete={handleScanComplete} />
            </div>
          )}
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={() => setShowScanDialog(false)}>Cancel</Button>
            <Button type="submit" disabled={submitMutation.isPending || !!activeJobId}>
              {submitMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Play className="h-4 w-4 mr-1" />}
              Start Scan
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
