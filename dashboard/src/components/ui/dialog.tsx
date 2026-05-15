import { type ReactNode, useEffect } from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Dialog({ open, onClose, title, children, className }: DialogProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    if (open) document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/40" onClick={onClose} />
      <div role="dialog" aria-modal="true" aria-label={title} className={cn("relative z-50 w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-xl border bg-background shadow-xl", className)}>
        {title && (
          <div className="flex items-center justify-between border-b px-6 py-4">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button onClick={onClose} className="rounded p-1 hover:bg-muted">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

/* ── Tabs (simple, compound-component style) ───────────────── */

interface TabsProps {
  value: string;
  onChange: (v: string) => void;
  children: ReactNode;
}

export function Tabs({ children }: TabsProps) {
  return <div>{children}</div>;
}

export function TabsList({ children }: { children: ReactNode }) {
  return <div className="flex gap-1 border-b mb-4">{children}</div>;
}

interface TabsTriggerProps {
  value: string;
  label: string;
  icon?: ReactNode;
  active?: boolean;
  onClick?: () => void;
}

export function TabsTrigger({ label, icon, active, onClick }: TabsTriggerProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
        active
          ? "border-primary text-primary"
          : "border-transparent text-muted-foreground hover:text-foreground"
      )}
    >
      {icon}
      {label}
    </button>
  );
}

export function TabsContent({ active, children }: { active: boolean; children: ReactNode }) {
  if (!active) return null;
  return <div>{children}</div>;
}
