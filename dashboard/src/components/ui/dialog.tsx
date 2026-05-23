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
    <div
      style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div data-testid="dialog-backdrop" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.65)", backdropFilter: "blur(4px)" }} onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{
          position: "relative", zIndex: 51, width: "100%", maxWidth: "780px",
          maxHeight: "90vh", overflowY: "auto", borderRadius: 14,
          background: "var(--bg-2)", border: "1px solid var(--border-2)",
          boxShadow: "0 24px 64px rgba(0,0,0,0.8)", margin: "0 16px",
        }}
        className={cn("", className)}
      >
        {title && (
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "18px 24px", borderBottom: "1px solid var(--border)",
            position: "sticky", top: 0, background: "var(--bg-2)", zIndex: 1,
          }}>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "var(--fg)" }}>{title}</h2>
            <button onClick={onClose} className="modal-close" aria-label="Close">
              <X size={15} />
            </button>
          </div>
        )}
        <div style={{ padding: 24 }}>{children}</div>
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
