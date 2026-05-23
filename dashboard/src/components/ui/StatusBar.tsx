import { useDensity } from "@/lib/useDensity";
import { AlignJustify, AlignLeft } from "lucide-react";

interface StatusBarItem {
  label: string;
  value: string | number;
  color?: string;
}

interface StatusBarProps {
  items?: StatusBarItem[];
  right?: React.ReactNode;
}

export function StatusBar({ items = [], right }: StatusBarProps) {
  const { density, toggle } = useDensity();

  return (
    <div style={{
      position: "fixed",
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 20,
      height: 26,
      background: "rgba(10,10,12,0.95)",
      borderTop: "1px solid var(--border)",
      backdropFilter: "blur(10px)",
      display: "flex",
      alignItems: "center",
      paddingInline: 16,
      gap: 16,
      fontSize: 11,
      fontFamily: "var(--mono)",
      color: "var(--fg-5)",
    }}>
      {items.map((item) => (
        <span key={item.label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span>{item.label}</span>
          <span style={{ color: item.color ?? "var(--fg-3)", fontWeight: 600 }}>{item.value}</span>
        </span>
      ))}

      <span style={{ flex: 1 }} />

      {right}

      <button
        onClick={toggle}
        title={`Switch to ${density === "comfortable" ? "compact" : "comfortable"} density`}
        style={{
          background: "transparent", border: "none",
          color: "var(--fg-4)", cursor: "pointer",
          display: "flex", alignItems: "center", gap: 4,
          fontSize: 10, fontFamily: "var(--mono)",
          padding: "2px 4px",
        }}
        aria-label={`Density: ${density}`}
      >
        {density === "comfortable"
          ? <AlignJustify size={11} aria-hidden />
          : <AlignLeft size={11} aria-hidden />}
        {density}
      </button>
    </div>
  );
}
