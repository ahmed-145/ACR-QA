import { useEffect } from "react";

type Handler = (e: KeyboardEvent) => void;

interface Shortcut {
  key: string;
  meta?: boolean;
  ctrl?: boolean;
  shift?: boolean;
  handler: Handler;
  preventDefault?: boolean;
}

export function useShortcuts(shortcuts: Shortcut[], enabled = true) {
  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (e: KeyboardEvent) => {
      const active = document.activeElement;
      const isInput = active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement || active instanceof HTMLSelectElement;

      for (const s of shortcuts) {
        const keyMatch = e.key === s.key || e.key.toLowerCase() === s.key.toLowerCase();
        const metaMatch = s.meta ? (e.metaKey || e.ctrlKey) : true;
        const ctrlMatch = s.ctrl ? e.ctrlKey : true;
        const shiftMatch = s.shift ? e.shiftKey : true;

        if (keyMatch && metaMatch && ctrlMatch && shiftMatch) {
          if (isInput && !s.meta && !s.ctrl) continue;
          if (s.preventDefault) e.preventDefault();
          s.handler(e);
          break;
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [shortcuts, enabled]);
}
