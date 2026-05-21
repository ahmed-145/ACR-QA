import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRuns } from "@/lib/queries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GitCompare, Loader2 } from "lucide-react";

export function ComparePage() {
  const navigate = useNavigate();
  const { data, isLoading } = useRuns(50);
  const [selectedA, setSelectedA] = useState<number | null>(null);
  const [selectedB, setSelectedB] = useState<number | null>(null);

  const runs = data?.runs ?? [];

  function handleCompare() {
    if (!selectedA || !selectedB) return;
    navigate(`/runs/${selectedA}/compare?compare=${selectedB}`);
  }

  function toggleSelect(id: number) {
    if (selectedA === id) { setSelectedA(null); return; }
    if (selectedB === id) { setSelectedB(null); return; }
    if (!selectedA) { setSelectedA(id); return; }
    if (!selectedB) { setSelectedB(id); return; }
    setSelectedA(selectedB);
    setSelectedB(id);
  }

  function selLabel(id: number) {
    if (selectedA === id) return "A";
    if (selectedB === id) return "B";
    return null;
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <GitCompare className="h-6 w-6" aria-hidden />
          Compare Runs
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Select two scans to diff their findings — fixed, introduced, and unchanged.
        </p>
      </div>

      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium">Run A:</span>
              {selectedA ? (
                <Badge variant="default">#{selectedA}</Badge>
              ) : (
                <span className="text-muted-foreground">not selected</span>
              )}
            </div>
            <span className="text-muted-foreground">vs</span>
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium">Run B:</span>
              {selectedB ? (
                <Badge variant="secondary">#{selectedB}</Badge>
              ) : (
                <span className="text-muted-foreground">not selected</span>
              )}
            </div>
            <Button
              className="ml-auto"
              disabled={!selectedA || !selectedB}
              onClick={handleCompare}
            >
              <GitCompare className="h-4 w-4 mr-1.5" aria-hidden />
              Compare
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="flex justify-center py-12 text-muted-foreground gap-2">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading scans…
        </div>
      ) : runs.length === 0 ? (
        <p className="text-center py-12 text-muted-foreground">No scans available yet.</p>
      ) : (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Select two runs (click to toggle A / B)</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y">
              {runs.map((r) => {
                const label = selLabel(r.id);
                return (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => toggleSelect(r.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 text-left text-sm transition-colors hover:bg-muted/50 ${label ? "bg-primary/5" : ""}`}
                  >
                    {label ? (
                      <Badge variant={label === "A" ? "default" : "secondary"} className="w-7 justify-center shrink-0">
                        {label}
                      </Badge>
                    ) : (
                      <div className="w-7 h-6 rounded border border-dashed border-muted-foreground/30 shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">#{r.id}</span>
                        <span className="text-muted-foreground truncate">{r.repo_name}</span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {new Date(r.started_at).toLocaleString()} · {r.total_findings} findings
                      </div>
                    </div>
                    <div className="flex gap-1.5 shrink-0">
                      {r.high_count > 0 && (
                        <Badge variant="destructive" className="text-[10px] px-1.5">{r.high_count}H</Badge>
                      )}
                      <Badge variant="outline" className="text-[10px] px-1.5 capitalize">{r.status}</Badge>
                    </div>
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
