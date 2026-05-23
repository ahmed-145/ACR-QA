import { type ReactNode, useEffect, useRef } from "react";
import { X } from "lucide-react";

interface SidePanelProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  width?: number;
  children: ReactNode;
}

export function SidePanel({ open, onClose, title, width = 480, children }: SidePanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  return (
    <>
      {/* Backdrop */}
      <div
        data-testid="side-panel-backdrop"
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 40,
          background: "rgba(0,0,0,0.5)",
          backdropFilter: "blur(2px)",
          opacity: open ? 1 : 0,
          pointerEvents: open ? "auto" : "none",
          transition: "opacity 0.2s",
        }}
      />
      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          width,
          maxWidth: "95vw",
          zIndex: 41,
          background: "var(--bg-2)",
          borderLeft: "1px solid var(--border-2)",
          display: "flex",
          flexDirection: "column",
          transform: open ? "translateX(0)" : `translateX(${width}px)`,
          transition: "transform 0.25s cubic-bezier(0.32,0.72,0,1)",
          boxShadow: "-24px 0 64px rgba(0,0,0,0.6)",
        }}
      >
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "16px 20px", borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}>
          {title && <span style={{ fontSize: 14, fontWeight: 600, color: "var(--fg)" }}>{title}</span>}
          <button
            onClick={onClose}
            className="btn-icon modal-close"
            aria-label="Close panel"
            style={{ marginLeft: "auto" }}
          >
            <X size={14} aria-hidden />
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
          {open && children}
        </div>
      </div>
    </>
  );
}
