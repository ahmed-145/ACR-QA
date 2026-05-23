import { create } from "zustand";
import { useEffect } from "react";
import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from "lucide-react";

export type ToastVariant = "success" | "error" | "info" | "warning";

interface ToastItem {
  id: string;
  title: string;
  variant: ToastVariant;
  duration?: number;
}

interface ToastStore {
  toasts: ToastItem[];
  add: (t: Omit<ToastItem, "id">) => void;
  remove: (id: string) => void;
}

const useToastStore = create<ToastStore>()((set) => ({
  toasts: [],
  add: (t) => set((s) => ({ toasts: [...s.toasts, { ...t, id: Math.random().toString(36).slice(2) }] })),
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export function toast(message: string, variant: ToastVariant = "info") {
  useToastStore.getState().add({ title: message, variant, duration: 3500 });
}

const ICONS: Record<ToastVariant, React.ReactNode> = {
  success: <CheckCircle  size={14} style={{ color: "var(--low)",  flexShrink: 0 }} aria-hidden />,
  error:   <AlertCircle  size={14} style={{ color: "var(--high)", flexShrink: 0 }} aria-hidden />,
  warning: <AlertTriangle size={14} style={{ color: "var(--med)", flexShrink: 0 }} aria-hidden />,
  info:    <Info          size={14} style={{ color: "var(--blue)", flexShrink: 0 }} aria-hidden />,
};

const BORDER: Record<ToastVariant, string> = {
  success: "var(--low-bdr)",
  error:   "var(--high-bdr)",
  warning: "var(--med-bdr)",
  info:    "rgba(96,165,250,0.25)",
};

function ToastEntry({ t }: { t: ToastItem }) {
  const remove = useToastStore((s) => s.remove);
  useEffect(() => {
    const timer = setTimeout(() => remove(t.id), t.duration ?? 3500);
    return () => clearTimeout(timer);
  }, [t.id, t.duration, remove]);

  return (
    <div
      role="alert"
      aria-live="polite"
      style={{
        minWidth: 260, maxWidth: 360,
        background: "var(--bg-3)",
        border: `1px solid ${BORDER[t.variant]}`,
        borderRadius: 10,
        padding: "11px 14px",
        display: "flex", alignItems: "center", gap: 10,
        boxShadow: "0 8px 24px rgba(0,0,0,0.6)",
        animation: "acr-fadein 0.18s ease",
        fontSize: 13, color: "var(--fg-2)",
      }}
    >
      {ICONS[t.variant]}
      <span style={{ flex: 1, fontWeight: 500 }}>{t.title}</span>
      <button
        onClick={() => remove(t.id)}
        aria-label="Dismiss"
        style={{ background: "transparent", border: "none", color: "var(--fg-5)", cursor: "pointer", display: "flex", padding: 0 }}
      >
        <X size={12} aria-hidden />
      </button>
    </div>
  );
}

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  if (!toasts.length) return null;
  return (
    <div
      className="toast-container"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((t) => <ToastEntry key={t.id} t={t} />)}
    </div>
  );
}
