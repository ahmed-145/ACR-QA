import { useParams, useNavigate } from "react-router-dom";
import { useFindings, useStats, useSupplyChain, usePrRisk, useCostBenefit, useReviewBottleneck } from "@/lib/queries";
import { FindingsTable } from "@/components/findings/FindingsTable";
import { FindingModal } from "@/components/findings/FindingModal";
import { OwaspHeatmap } from "@/components/compliance/OwaspHeatmap";
import { RiskHeatmap } from "@/components/findings/RiskHeatmap";
import { VulnerabilityTimeline } from "@/components/findings/VulnerabilityTimeline";
import { DependencyTree } from "@/components/supply/DependencyTree";
import { SbomDownload } from "@/components/supply/SbomDownload";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/dialog";
import { Loader2, ArrowLeft, Shield, Package, BarChart3, FileDown, GitPullRequest, TrendingUp, Map } from "lucide-react";
import { type Finding } from "@/lib/api";
import { useState } from "react";
import { severityColor } from "@/lib/utils";
import { useTranslation } from "react-i18next";
import { SkeletonCard } from "@/components/ui/skeleton";

export function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);
  const navigate = useNavigate();
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [activeTab, setActiveTab] = useState("findings");
  const { t } = useTranslation();

  const { data: findingsData, isLoading: findingsLoading } = useFindings(runId);
  const { data: stats, isLoading: statsLoading } = useStats(runId);
  const { data: supplyChain, isLoading: scLoading } = useSupplyChain(runId);
  const { data: prRisk } = usePrRisk(runId);
  const { data: costBenefit } = useCostBenefit(runId);
  const { data: reviewBottleneck } = useReviewBottleneck(runId);

  const findings = findingsData?.findings ?? [];

  const severityCounts = findings.reduce(
    (acc, f) => { acc[f.severity] = (acc[f.severity] ?? 0) + 1; return acc; },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Run #{runId}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Detailed analysis results</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {(["HIGH", "MEDIUM", "LOW"] as const).map((sev) =>
            severityCounts[sev] ? (
              <Badge key={sev} className={severityColor(sev)}>
                {severityCounts[sev]} {sev}
              </Badge>
            ) : null
          )}
          <Button
            variant="outline"
            size="sm"
            aria-label="View risk map"
            onClick={() => navigate(`/runs/${runId}/risk-map`)}
          >
            <Map className="h-4 w-4 mr-1" aria-hidden />
            Risk Map
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="no-print"
            aria-label={t("common.exportPdf")}
            onClick={() => window.print()}
          >
            <FileDown className="h-4 w-4 mr-1" aria-hidden />
            {t("common.exportPdf")}
          </Button>
        </div>
      </div>

      {/* Stats row */}
      {statsLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)}
        </div>
      ) : stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Total Findings", value: stats.total_findings },
            { label: "HIGH", value: stats.high, danger: stats.high > 0 },
            { label: "MEDIUM", value: stats.medium },
            { label: "LOW", value: stats.low },
          ].map(({ label, value, danger }) => (
            <Card key={label}>
              <CardContent className="pt-4">
                <div className={`text-2xl font-bold ${danger ? "text-red-600" : ""}`}>{value}</div>
                <div className="text-xs text-muted-foreground mt-1">{label}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {/* Tabs */}
      <Tabs value={activeTab} onChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="findings" icon={<Shield className="h-3.5 w-3.5" />} label="Findings" active={activeTab === "findings"} onClick={() => setActiveTab("findings")} />
          <TabsTrigger value="compliance" icon={<BarChart3 className="h-3.5 w-3.5" />} label="OWASP" active={activeTab === "compliance"} onClick={() => setActiveTab("compliance")} />
          <TabsTrigger value="supply" icon={<Package className="h-3.5 w-3.5" />} label="Supply Chain" active={activeTab === "supply"} onClick={() => setActiveTab("supply")} />
          <TabsTrigger value="heatmap" icon={<BarChart3 className="h-3.5 w-3.5" />} label="Heatmap" active={activeTab === "heatmap"} onClick={() => setActiveTab("heatmap")} />
          <TabsTrigger value="timeline" icon={<BarChart3 className="h-3.5 w-3.5" />} label="Timeline" active={activeTab === "timeline"} onClick={() => setActiveTab("timeline")} />
          <TabsTrigger value="pr-risk" icon={<GitPullRequest className="h-3.5 w-3.5" />} label="PR Risk" active={activeTab === "pr-risk"} onClick={() => setActiveTab("pr-risk")} />
          <TabsTrigger value="analytics" icon={<TrendingUp className="h-3.5 w-3.5" />} label="Analytics" active={activeTab === "analytics"} onClick={() => setActiveTab("analytics")} />
        </TabsList>

        <TabsContent active={activeTab === "findings"}>
          {findingsLoading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground gap-2">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading findings…
            </div>
          ) : (
            <FindingsTable findings={findings} onSelect={setSelectedFinding} />
          )}
        </TabsContent>

        <TabsContent active={activeTab === "compliance"}>
          <Card>
            <CardContent className="pt-4">
              <OwaspHeatmap runId={runId} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent active={activeTab === "supply"}>
          {scLoading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground gap-2">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading supply chain…
            </div>
          ) : supplyChain ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  {supplyChain.dependencies.length} dependencies analysed
                </div>
                <SbomDownload runId={runId} />
              </div>
              <DependencyTree deps={supplyChain.dependencies} />
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">No supply-chain data</div>
          )}
        </TabsContent>

        <TabsContent active={activeTab === "heatmap"}>
          <Card>
            <CardContent className="pt-4">
              <RiskHeatmap runId={runId} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent active={activeTab === "timeline"}>
          <Card>
            <CardContent className="pt-4">
              <VulnerabilityTimeline limit={30} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent active={activeTab === "pr-risk"}>
          {prRisk ? (
            <div className="space-y-4">
              {/* Score banner */}
              <Card>
                <CardContent className="pt-6 pb-6">
                  <div className="flex items-center gap-6">
                    <div className={`text-6xl font-black tabular-nums ${prRisk.band === "red" ? "text-red-600" : prRisk.band === "yellow" ? "text-yellow-500" : "text-green-600"}`}>
                      {prRisk.score}
                    </div>
                    <div>
                      <Badge className={`text-sm px-3 py-1 ${prRisk.band === "red" ? "bg-red-100 text-red-700" : prRisk.band === "yellow" ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"}`}>
                        {prRisk.band.toUpperCase()} RISK
                      </Badge>
                      <p className="text-sm text-muted-foreground mt-1">Merge risk score (0 = safe, 100 = block)</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              {/* Contributions */}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Risk Contributions</CardTitle></CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(prRisk.contributions).map(([key, val]) => (
                      <div key={key} className="flex items-center gap-3">
                        <span className="text-xs text-muted-foreground w-40 shrink-0">{key.replace(/_/g, " ")}</span>
                        <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                          <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, (val as number) * 100)}%` }} />
                        </div>
                        <span className="text-xs tabular-nums w-10 text-right">{((val as number) * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
              {/* Explainer bullets */}
              {prRisk.explainer.length > 0 && (
                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-sm">Why this score?</CardTitle></CardHeader>
                  <CardContent>
                    <ul className="space-y-1 text-sm">
                      {prRisk.explainer.map((line, i) => <li key={i} className="flex gap-2"><span className="text-muted-foreground">•</span>{line}</li>)}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center py-16 text-muted-foreground gap-2">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading PR risk…
            </div>
          )}
        </TabsContent>

        <TabsContent active={activeTab === "analytics"}>
          <div className="grid md:grid-cols-2 gap-4">
            {/* Cost-Benefit */}
            {costBenefit && (
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Cost-Benefit Analysis</CardTitle></CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {[
                      { label: "Analysis cost", value: `$${costBenefit.analysis_cost_usd.toFixed(4)}` },
                      { label: "Developer hours saved", value: `${costBenefit.hours_saved.toFixed(1)} h` },
                      { label: "Dev cost saved", value: `$${costBenefit.dev_cost_saved_usd.toFixed(2)}` },
                      { label: "ROI multiplier", value: costBenefit.roi_multiplier },
                      { label: "Cost per finding", value: costBenefit.total_findings > 0 ? `$${costBenefit.cost_per_finding.toFixed(4)}` : "—" },
                    ].map(({ label, value }) => (
                      <div key={label} className="flex justify-between text-sm border-b last:border-0 pb-2 last:pb-0">
                        <span className="text-muted-foreground">{label}</span>
                        <span className="font-medium tabular-nums">{value}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
            {/* Review Bottleneck */}
            {reviewBottleneck && (
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Review Bottleneck</CardTitle></CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {[
                      { label: "Median time to first review", value: `${reviewBottleneck.median_time_to_first_review_hours.toFixed(1)} h` },
                      { label: "Reviewer load Gini", value: reviewBottleneck.reviewer_load_gini.toFixed(2) },
                      { label: "Merged without comment", value: `${(reviewBottleneck.pct_merged_without_comment * 100).toFixed(0)}%` },
                      { label: "Top-3 reviewer share", value: `${(reviewBottleneck.top3_reviewer_share * 100).toFixed(0)}%` },
                      { label: "Stale PRs", value: `${reviewBottleneck.stale_pr_count}` },
                      { label: "Commits analysed", value: `${reviewBottleneck.total_commits_analyzed}` },
                    ].map(({ label, value }) => (
                      <div key={label} className="flex justify-between text-sm border-b last:border-0 pb-2 last:pb-0">
                        <span className="text-muted-foreground">{label}</span>
                        <span className="font-medium tabular-nums">{value}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Finding detail modal */}
      {selectedFinding && (
        <FindingModal
          finding={selectedFinding}
          runId={runId}
          onClose={() => setSelectedFinding(null)}
        />
      )}
    </div>
  );
}
