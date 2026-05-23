import { type ReactNode, useState, useRef } from "react";

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  placement?: "top" | "bottom" | "left" | "right";
  delay?: number;
}

export function Tooltip({ content, children, placement = "top", delay = 400 }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = () => {
    timerRef.current = setTimeout(() => setVisible(true), delay);
  };

  const hide = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setVisible(false);
  };

  const placementStyles: Record<typeof placement, React.CSSProperties> = {
    top:    { bottom: "calc(100% + 6px)", left: "50%", transform: "translateX(-50%)" },
    bottom: { top: "calc(100% + 6px)",    left: "50%", transform: "translateX(-50%)" },
    left:   { right: "calc(100% + 6px)",  top: "50%",  transform: "translateY(-50%)" },
    right:  { left: "calc(100% + 6px)",   top: "50%",  transform: "translateY(-50%)" },
  };

  return (
    <span
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {visible && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            zIndex: 9999,
            pointerEvents: "none",
            ...placementStyles[placement],
            background: "var(--bg-3)",
            border: "1px solid var(--border-2)",
            borderRadius: 6,
            padding: "5px 9px",
            fontSize: 12,
            color: "var(--fg-2)",
            whiteSpace: "nowrap",
            boxShadow: "0 4px 16px rgba(0,0,0,0.6)",
            animation: "acr-fadein 0.12s ease",
          }}
        >
          {content}
        </span>
      )}
    </span>
  );
}
