import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { useApiKeys, useCreateApiKey, useDeleteApiKey } from "@/lib/queries";
import { deleteAccount } from "@/lib/api";
import { CheckCircle, XCircle, Loader2, Trash2, Plus } from "lucide-react";
import { toast } from "@/components/ui/toast";

type HealthStatus = "checking" | "ok" | "error";

function useHealthCheck(url: string) {
  const [status, setStatus] = useState<HealthStatus>("checking");
  useEffect(() => {
    const check = async () => {
      setStatus("checking");
      try {
        const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
        setStatus(res.ok ? "ok" : "error");
      } catch {
        setStatus("error");
      }
    };
    check();
    const interval = setInterval(check, 30_000);
    return () => clearInterval(interval);
  }, [url]);
  return status;
}

function StatusDot({ status }: { status: HealthStatus }) {
  if (status === "checking") return <Loader2 size={14} className="animate-spin" style={{ color: "var(--fg-4)" }} />;
  if (status === "ok") return <CheckCircle size={14} style={{ color: "var(--low)" }} />;
  return <XCircle size={14} style={{ color: "var(--high)" }} />;
}

export function SettingsPage() {
  const { user, logout } = useAuth();
  const mode = import.meta.env.VITE_ACRQA_MODE ?? "online";
  const isOffline = mode === "offline";

  const apiStatus = useHealthCheck("/health");
  const celeryStatus = useHealthCheck("/health");

  const { data: apiKeys, isLoading: keysLoading } = useApiKeys();
  const createKey = useCreateApiKey();
  const deleteKey = useDeleteApiKey();

  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  function handleLogout() {
    logout();
    window.location.href = "/login";
  }

  function handleCopyToken() {
    const raw = localStorage.getItem("acrqa_auth");
    if (!raw) return;
    try {
      const { state } = JSON.parse(raw);
      navigator.clipboard.writeText(state.token ?? "").then(() => toast("Token copied", "success"));
    } catch {
      toast("Failed to copy token", "error");
    }
  }

  async function handleCreateKey(e: React.FormEvent) {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    try {
      const result = await createKey.mutateAsync(newKeyName.trim());
      setNewKeyValue(result.key);
      setNewKeyName("");
      toast("API key created", "success");
    } catch {
      toast("Failed to create key", "error");
    }
  }

  async function handleDeleteKey(id: number) {
    try {
      await deleteKey.mutateAsync(id);
      toast("Key revoked", "success");
    } catch {
      toast("Failed to revoke key", "error");
    }
  }

  async function handleDeleteAccount() {
    try {
      await deleteAccount();
      logout();
      window.location.href = "/login";
    } catch {
      toast("Failed to delete account", "error");
    }
  }

  return (
    <>
      <div className="topbar">
        <div className="crumbs">
          <span className="cur">Settings</span>
        </div>
      </div>

      <div className="page-pad" style={{ maxWidth: 720 }}>
        <h1 className="title">Settings</h1>
        <p className="subtitle">System status and account configuration</p>

        {/* Operation Mode */}
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <span className="panel-title">Operation Mode</span>
            <span className="panel-sub" style={{ color: isOffline ? "var(--med)" : "var(--low)" }}>
              {mode.toUpperCase()}
            </span>
          </div>
          {isOffline && (
            <p style={{ fontSize: 12, color: "var(--fg-4)", margin: 0, lineHeight: 1.6 }}>
              Offline mode: LLM calls routed to local Ollama endpoint.
              Set <code style={{ fontFamily: "var(--mono)", color: "var(--purple)" }}>ACRQA_LLM_PROVIDER=ollama</code> and{" "}
              <code style={{ fontFamily: "var(--mono)", color: "var(--purple)" }}>ACRQA_MODE=offline</code> in the backend environment.
            </p>
          )}
        </div>

        {/* Live Status */}
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <span className="panel-title">Live Status</span>
          </div>
          {[
            { label: "FastAPI backend", status: apiStatus },
            { label: "Celery worker", status: celeryStatus },
          ].map(({ label, status }) => (
            <div key={label} className="setting-row">
              <span className="lbl">{label}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <StatusDot status={status} />
                <span className="val">{status === "checking" ? "checking…" : status === "ok" ? "healthy" : "unreachable"}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Account */}
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <span className="panel-title">Account</span>
          </div>
          {user && (
            <>
              <div className="setting-row">
                <span className="lbl">Email</span>
                <span className="val">{user.email}</span>
              </div>
              <div className="setting-row">
                <span className="lbl">Role</span>
                <span className="val">{user.role ?? "analyst"}</span>
              </div>
            </>
          )}
          <div style={{ display: "flex", gap: 8, paddingTop: 12 }}>
            <button className="btn-ghost" onClick={handleCopyToken}>Copy API token</button>
            <button className="btn-danger" onClick={handleLogout}>Sign out</button>
          </div>
        </div>

        {/* API Keys */}
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <span className="panel-title">API Keys</span>
          </div>
          <p style={{ fontSize: 12, color: "var(--fg-4)", marginBottom: 16, marginTop: 0 }}>
            Use API keys for CI/CD integrations. Keys are shown once — store them securely.
          </p>

          {newKeyValue && (
            <div style={{ background: "rgba(16,185,129,0.08)", border: "1px solid var(--low-bdr)", borderRadius: 8, padding: "12px 14px", marginBottom: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: "var(--low-fg)", marginTop: 0, marginBottom: 8 }}>
                New key created — copy it now, it won't be shown again:
              </p>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <code style={{ flex: 1, fontFamily: "var(--mono)", fontSize: 12, background: "var(--bg)", padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {newKeyValue}
                </code>
                <button className="btn-ghost" style={{ height: 28, padding: "0 10px", fontSize: 12 }} onClick={() => { navigator.clipboard.writeText(newKeyValue); toast("Copied", "success"); }}>Copy</button>
              </div>
              <button style={{ fontSize: 11.5, color: "var(--fg-4)", background: "none", border: "none", cursor: "pointer", marginTop: 6, padding: 0 }} onClick={() => setNewKeyValue(null)}>Dismiss</button>
            </div>
          )}

          {keysLoading ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--fg-4)", fontSize: 13 }}>
              <span className="spinner" /> Loading…
            </div>
          ) : apiKeys && apiKeys.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
              {apiKeys.map((k) => (
                <div key={k.id} className="key-row">
                  <span className="key-name">{k.name}</span>
                  <span className="key-prefix">{k.prefix}…</span>
                  <span className="key-date">{k.last_used_at ? `Used ${new Date(k.last_used_at).toLocaleDateString()}` : "Never used"}</span>
                  <button
                    className="btn-icon"
                    style={{ width: 28, height: 28, borderColor: "var(--high-bdr)", color: "var(--high-fg)" }}
                    aria-label="Revoke key"
                    onClick={() => handleDeleteKey(k.id)}
                  >
                    <Trash2 size={12} aria-hidden />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 13, color: "var(--fg-4)", marginBottom: 16 }}>No API keys yet.</p>
          )}

          <form onSubmit={handleCreateKey} style={{ display: "flex", gap: 8 }}>
            <input
              className="inp"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g. github-actions)"
            />
            <button type="submit" className="btn-prim" aria-label="Create API key" disabled={createKey.isPending || !newKeyName.trim()}>
              {createKey.isPending ? <span className="spinner" style={{ width: 14, height: 14 }} aria-hidden /> : <Plus size={14} aria-hidden />}
            </button>
          </form>
        </div>

        {/* Danger zone */}
        <div className="panel" style={{ border: "1px solid var(--high-bdr)" }}>
          <div className="panel-head">
            <span className="panel-title" style={{ color: "var(--high-fg)" }}>Danger Zone</span>
          </div>
          <p style={{ fontSize: 13, color: "var(--fg-4)", marginBottom: 12 }}>
            Permanently delete your account and all associated data. This cannot be undone.
          </p>
          {!deleteConfirm ? (
            <button className="btn-danger" onClick={() => setDeleteConfirm(true)}>Delete my account</button>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--high-fg)", margin: 0 }}>Are you sure? This is irreversible.</p>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn-danger" onClick={handleDeleteAccount}>Yes, delete everything</button>
                <button className="btn-ghost" onClick={() => setDeleteConfirm(false)}>Cancel</button>
              </div>
            </div>
          )}
        </div>

        <div style={{ textAlign: "center", fontSize: 11.5, color: "var(--fg-5)", marginTop: 32 }}>
          ACR-QA v5.0.0b1 · Phase A complete
        </div>
      </div>
    </>
  );
}
