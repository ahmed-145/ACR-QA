import { useParams, useNavigate } from "react-router-dom";
import { useRiskMap } from "@/lib/queries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, RefreshCw, Loader2, AlertTriangle } from "lucide-react";
import { useState } from "react";

function scoreBand(score: number): { label: string; variant: "destructive" | "default" | "secondary" | "outline" } {
  if (score >= 75) return { label: "Critical", variant: "destructive" };
  if (score >= 50) return { label: "High", variant: "default" };
  if (score >= 25) return { label: "Medium", variant: "secondary" };
  return { label: "Low", variant: "outline" };
}

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 75 ? "bg-red-500" :
    score >= 50 ? "bg-orange-400" :
    score >= 25 ? "bg-yellow-400" :
    "bg-green-400";
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs tabular-nums w-8 text-right">{score}</span>
    </div>
  );
}

export function RiskMapPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const runId = Number(id);
  const [refresh, setRefresh] = useState(false);
  const { data, isLoading, error, refetch } = useRiskMap(runId, refresh);

  const files = data?.files ?? [];
  const sorted = [...files].sort((a, b) => b.score - a.score);
  const topRisk = sorted.slice(0, 5);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(`/runs/${runId}`)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Risk Map</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Run #{runId} · Per-file heuristic risk scores (0–100)
            {data && <span className="ml-2 text-xs">{data.cached ? "· cached" : "· computed"}</span>}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => { setRefresh(true); refetch(); }}
          disabled={isLoading}
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RefreshCw className="h-4 w-4 mr-1" />}
          Refresh
        </Button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-16 text-muted-foreground gap-2">
          <Loader2 className="h-5 w-5 animate-spin" /> Computing risk scores…
        </div>
      )}

      {error && (
        <Card className="border-red-200">
          <CardContent className="pt-4 flex items-center gap-2 text-red-600 text-sm">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Failed to load risk map. The run may have no findings yet.
          </CardContent>
        </Card>
      )}

      {data && !isLoading && (
        <>
          {/* Summary row */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {[
              { label: "Files Analyzed", value: data.total_files },
              { label: "Critical (≥75)", value: files.filter((f) => f.score >= 75).length, danger: true },
              { label: "High (50–74)", value: files.filter((f) => f.score >= 50 && f.score < 75).length },
              { label: "Avg Score", value: files.length ? Math.round(files.reduce((s, f) => s + f.score, 0) / files.length) : 0 },
            ].map(({ label, value, danger }) => (
              <Card key={label}>
                <CardContent className="pt-4">
                  <div className={`text-2xl font-bold ${danger && Number(value) > 0 ? "text-red-600" : ""}`}>{value}</div>
                  <div className="text-xs text-muted-foreground mt-1">{label}</div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Top 5 hotspots */}
          {topRisk.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-orange-500" aria-hidden />
                  Top Risk Hotspots
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {topRisk.map((f) => {
                  const { label, variant } = scoreBand(f.score);
                  return (
                    <div key={f.file_path} className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={variant} className="text-[10px] px-1.5 shrink-0">{label}</Badge>
                        <span className="font-mono text-xs truncate flex-1">{f.file_path}</span>
                      </div>
                      <ScoreBar score={f.score} />
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* Full file table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">All Files ({files.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y max-h-[600px] overflow-y-auto">
                {sorted.map((f) => {
                  const { label, variant } = scoreBand(f.score);
                  const topContrib = Object.entries(f.contributions ?? {})
                    .sort(([, a], [, b]) => (b as number) - (a as number))
                    .slice(0, 3)
                    .filter(([, v]) => (v as number) > 0);
                  return (
                    <div key={f.file_path} className="px-4 py-3 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <Badge variant={variant} className="text-[10px] px-1.5 shrink-0">{label}</Badge>
                        <span className="font-mono text-xs truncate flex-1">{f.file_path}</span>
                      </div>
                      <ScoreBar score={f.score} />
                      {topContrib.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-0.5">
                          {topContrib.map(([k, v]) => (
                            <span key={k} className="text-[10px] bg-muted rounded px-1.5 py-0.5 text-muted-foreground">
                              {k}: {Number(v).toFixed(2)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
