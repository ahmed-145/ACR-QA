interface KbdProps {
  children: string;
}

export function Kbd({ children }: KbdProps) {
  return (
    <kbd style={{
      fontFamily: "var(--mono)",
      fontSize: 10,
      color: "var(--fg-4)",
      padding: "2px 5px",
      borderRadius: 4,
      background: "rgba(255,255,255,0.05)",
      border: "1px solid var(--border-2)",
      borderBottomWidth: 2,
      lineHeight: 1,
      display: "inline-block",
    }}>
      {children}
    </kbd>
  );
}

interface KbdHintProps {
  shortcut: string | string[];
  label?: string;
}

export function KbdHint({ shortcut, label }: KbdHintProps) {
  const keys = Array.isArray(shortcut) ? shortcut : [shortcut];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--fg-5)" }}>
      {label && <span>{label}</span>}
      {keys.map((k, i) => (
        <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 2 }}>
          {i > 0 && <span style={{ fontSize: 9, opacity: 0.5 }}>+</span>}
          <Kbd>{k}</Kbd>
        </span>
      ))}
    </span>
  );
}
