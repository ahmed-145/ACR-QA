import { useState } from "react";
import { Dialog, TabsList, TabsTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { type Finding } from "@/lib/api";
import { TaintFlowGraph } from "./TaintFlowGraph";
import { ReasoningChain } from "./ReasoningChain";
import { AutofixDiff } from "./AutofixDiff";
import { ExploitProofPanel } from "./ExploitProofPanel";
import { ChatSidebar } from "./ChatSidebar";
import { CallGraph } from "./CallGraph";
import { FindingHistory } from "./FindingHistory";

interface Props {
  finding: Finding | null;
  runId: number;
  onClose: () => void;
}

const TABS = ["Overview", "Chat", "Call Graph", "History", "Taint", "Reasoning", "Autofix", "Exploit"];

export function FindingModal({ finding, runId, onClose }: Props) {
  const [tab, setTab] = useState("Overview");

  if (!finding) return null;

  return (
    <Dialog open={!!finding} onClose={onClose} title={finding.rule_id} className="max-w-4xl">
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 items-center">
          <Badge variant={finding.severity as "high" | "medium" | "low" | "default"}>{finding.severity.toUpperCase()}</Badge>
          {finding.category && <Badge variant="secondary">{finding.category}</Badge>}
          {finding.tool && <span className="text-xs text-muted-foreground">via {finding.tool}</span>}
          <span className="ml-auto text-xs text-muted-foreground">
            Confidence: {Math.round((finding.confidence ?? 0) * 100)}%
          </span>
        </div>

        <div className="rounded bg-muted px-3 py-2 font-mono text-xs">
          {finding.file_path}{finding.line_number ? `:${finding.line_number}` : ""}
        </div>

        <TabsList>
          {TABS.map((t) => (
            <TabsTrigger
              key={t}
              value={t}
              label={t}
              active={tab === t}
              onClick={() => setTab(t)}
            />
          ))}
        </TabsList>

        {tab === "Overview" && (
          <div className="space-y-3">
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-1">Message</div>
              <p className="text-sm">{finding.message}</p>
            </div>
            {finding.explanation_text && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">AI Explanation</div>
                <div className="rounded-lg border bg-muted/20 p-3 text-sm whitespace-pre-wrap">
                  {finding.explanation_text}
                </div>
              </div>
            )}
            {finding.model_name && (
              <div className="text-xs text-muted-foreground">
                Model: {finding.model_name}
              </div>
            )}
          </div>
        )}

        {tab === "Chat" && <ChatSidebar findingId={finding.id} />}
        {tab === "Call Graph" && <CallGraph findingId={finding.id} />}
        {tab === "History" && <FindingHistory findingId={finding.id} />}
        {tab === "Taint" && <TaintFlowGraph finding={finding} />}
        {tab === "Reasoning" && <ReasoningChain finding={finding} />}
        {tab === "Autofix" && <AutofixDiff runId={runId} findingId={finding.id} />}
        {tab === "Exploit" && <ExploitProofPanel finding={finding} />}
      </div>
    </Dialog>
  );
}
