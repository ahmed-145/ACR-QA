import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Search, LayoutDashboard, Package, Settings, LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth";

type Command = {
  id: string;
  label: string;
  icon: React.ReactNode;
  action: () => void;
};

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { logout } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: Command[] = [
    { id: "scans", label: "Go to Scans", icon: <LayoutDashboard className="h-4 w-4" />, action: () => navigate("/") },
    { id: "supply", label: "Go to Supply Chain", icon: <Package className="h-4 w-4" />, action: () => navigate("/supply-chain") },
    { id: "settings", label: "Go to Settings", icon: <Settings className="h-4 w-4" />, action: () => navigate("/settings") },
    { id: "logout", label: "Sign out", icon: <LogOut className="h-4 w-4" />, action: () => { logout(); navigate("/login"); } },
  ];

  const filtered = query
    ? commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands;

  const [highlighted, setHighlighted] = useState(0);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
        setQuery("");
        setHighlighted(0);
      }
      if (e.key === "/" && !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        setOpen(true);
        setQuery("");
        setHighlighted(0);
      }
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (!open) return;
    const raf = requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
    return () => cancelAnimationFrame(raf);
  }, [open]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((h) => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter" && filtered[highlighted]) {
      filtered[highlighted].action();
      setOpen(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-black/40"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-md bg-background border rounded-xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="flex items-center gap-2 px-3 border-b">
          <Search className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setHighlighted(0); }}
            placeholder="Type a command…"
            className="flex-1 py-3 text-sm bg-transparent outline-none placeholder:text-muted-foreground"
          />
          <kbd className="text-[10px] text-muted-foreground border rounded px-1 py-0.5">ESC</kbd>
        </div>
        <div className="py-1 max-h-64 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="px-4 py-3 text-sm text-muted-foreground">No results</div>
          ) : (
            filtered.map((cmd, i) => (
              <button
                key={cmd.id}
                className={`w-full text-left flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  i === highlighted ? "bg-primary text-primary-foreground" : "hover:bg-muted"
                }`}
                onClick={() => { cmd.action(); setOpen(false); }}
                onMouseEnter={() => setHighlighted(i)}
              >
                {cmd.icon}
                {cmd.label}
              </button>
            ))
          )}
        </div>
        <div className="border-t px-3 py-2 flex items-center gap-3 text-[10px] text-muted-foreground">
          <span><kbd className="border rounded px-1">↑↓</kbd> navigate</span>
          <span><kbd className="border rounded px-1">↵</kbd> select</span>
          <span><kbd className="border rounded px-1">Esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
