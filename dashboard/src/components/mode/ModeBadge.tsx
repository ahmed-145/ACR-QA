import { Wifi, WifiOff } from "lucide-react";

export function ModeBadge() {
  const mode = import.meta.env.VITE_ACRQA_MODE ?? "online";
  const offline = mode === "offline";
  return (
    <button
      className="btn-icon"
      style={{ width: "auto", padding: "0 10px", gap: 6, fontSize: 11, fontWeight: 600, color: offline ? "var(--med-fg)" : "var(--low-fg)", borderColor: offline ? "var(--med-bdr)" : "var(--low-bdr)" }}
      aria-label={`Mode: ${mode}`}
      title={`Mode: ${mode}`}
    >
      {offline ? <WifiOff size={11} aria-hidden /> : <Wifi size={11} aria-hidden />}
      {offline ? "OFFLINE" : "ONLINE"}
    </button>
  );
}
