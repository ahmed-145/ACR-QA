import { useEffect } from "react";
import { X } from "lucide-react";

interface ShortcutsModalProps {
  open: boolean;
  onClose: () => void;
}

const SECTIONS = [
  {
    title: "Navigation",
    rows: [
      { keys: ["G", "H"], desc: "Go to Overview" },
      { keys: ["G", "S"], desc: "Go to Scans" },
      { keys: ["G", "F"], desc: "Go to All Findings" },
      { keys: ["G", "A"], desc: "Go to Analytics" },
    ],
  },
  {
    title: "Findings Table",
    rows: [
      { keys: ["J"], desc: "Move cursor down" },
      { keys: ["K"], desc: "Move cursor up" },
      { keys: ["O"], desc: "Open preview panel" },
      { keys: ["X"], desc: "Close preview panel" },
      { keys: ["Enter"], desc: "Open full run detail" },
      { keys: ["←", "→"], desc: "Previous / next page" },
    ],
  },
  {
    title: "Global",
    rows: [
      { keys: ["⌘", "K"], desc: "Open command palette" },
      { keys: ["?"], desc: "Show keyboard shortcuts" },
      { keys: ["Esc"], desc: "Close panel / modal" },
    ],
  },
];

export function ShortcutsModal({ open, onClose }: ShortcutsModalProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="shortcuts-modal-bg" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }} role="dialog" aria-modal aria-label="Keyboard shortcuts">
      <div className="shortcuts-modal">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 22 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fg)" }}>Keyboard Shortcuts</div>
          <button className="modal-close" onClick={onClose} aria-label="Close shortcuts"><X size={14} aria-hidden /></button>
        </div>
        {SECTIONS.map((s) => (
          <div key={s.title} className="shortcuts-section">
            <div className="shortcuts-section-title">{s.title}</div>
            {s.rows.map((r) => (
              <div key={r.desc} className="shortcut-row">
                <span className="shortcut-desc">{r.desc}</span>
                <span className="shortcut-keys">
                  {r.keys.map((k) => <kbd key={k} className="kbd">{k}</kbd>)}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
