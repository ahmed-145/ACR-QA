import { useParams, useNavigate } from "react-router-dom";
import { useFindings, useStats, useSupplyChain } from "@/lib/queries";
import { FindingsTable } from "@/components/findings/FindingsTable";
import { FindingModal } from "@/components/findings/FindingModal";
import { OwaspHeatmap } from "@/components/compliance/OwaspHeatmap";
import { DependencyTree } from "@/components/supply/DependencyTree";
import { SbomDownload } from "@/components/supply/SbomDownload";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/dialog";
import { Loader2, ArrowLeft, Shield, Package, BarChart3, FileDown } from "lucide-react";
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
            className="no-print ml-2"
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
