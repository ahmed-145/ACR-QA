import { type ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="empty" style={{ padding: "80px 20px", gap: 16 }}>
      {icon && (
        <div style={{
          width: 48, height: 48, borderRadius: 12,
          background: "rgba(167,139,250,0.08)",
          border: "1px solid rgba(167,139,250,0.20)",
          display: "grid", placeItems: "center",
          color: "var(--purple)",
        }}>
          {icon}
        </div>
      )}
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fg-2)", marginBottom: 6 }}>{title}</div>
        {description && <div style={{ fontSize: 13, color: "var(--fg-4)", maxWidth: 320, lineHeight: 1.5 }}>{description}</div>}
      </div>
      {action}
    </div>
  );
}
