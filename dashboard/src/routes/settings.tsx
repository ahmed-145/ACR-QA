import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";
import { useApiKeys, useCreateApiKey, useDeleteApiKey } from "@/lib/queries";
import { deleteAccount } from "@/lib/api";
import { Wifi, WifiOff, Server, User, Shield, CheckCircle, XCircle, Loader2, Key, Plus, Trash2 } from "lucide-react";
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
  if (status === "checking") return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />;
  if (status === "ok") return <CheckCircle className="h-4 w-4 text-green-600" />;
  return <XCircle className="h-4 w-4 text-red-500" />;
}

export function SettingsPage() {
  const { user, logout } = useAuth();
  const mode = import.meta.env.VITE_ACRQA_MODE ?? "online";
  const isOffline = mode === "offline";

  const apiStatus = useHealthCheck("/v1/health");
  const celeryStatus = useHealthCheck("/v1/celery/health");

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
    <div className="space-y-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">System status and account configuration</p>
      </div>

      {/* Mode card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            {isOffline ? <WifiOff className="h-4 w-4" /> : <Wifi className="h-4 w-4" />}
            Operation Mode
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm">Current mode</span>
            <Badge variant={isOffline ? "destructive" : "default"} className="uppercase text-xs">
              {mode}
            </Badge>
          </div>
          {isOffline && (
            <p className="text-xs text-muted-foreground bg-muted/50 rounded p-2">
              Offline mode: LLM calls routed to local Ollama endpoint. Set{" "}
              <code className="font-mono">ACRQA_LLM_PROVIDER=ollama</code> and{" "}
              <code className="font-mono">ACRQA_MODE=offline</code> in the backend environment.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Live status */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="h-4 w-4" /> Live Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { label: "FastAPI backend", status: apiStatus },
              { label: "Celery worker", status: celeryStatus },
            ].map(({ label, status }) => (
              <div key={label} className="flex items-center justify-between py-1 border-b last:border-0">
                <span className="text-sm">{label}</span>
                <div className="flex items-center gap-2">
                  <StatusDot status={status} />
                  <span className="text-xs text-muted-foreground">
                    {status === "checking" ? "checking" : status === "ok" ? "healthy" : "unreachable"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Account */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <User className="h-4 w-4" /> Account
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {user && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Email</span>
                <span className="text-sm font-medium">{user.email}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Role</span>
                <Badge variant="outline" className="text-xs">
                  <Shield className="h-3 w-3 mr-1" />
                  {user.role ?? "analyst"}
                </Badge>
              </div>
            </>
          )}
          <div className="flex gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={handleCopyToken}>
              Copy API token
            </Button>
            <Button variant="destructive" size="sm" onClick={handleLogout}>
              Sign out
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* API Keys */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Key className="h-4 w-4" /> API Keys
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">Use API keys for CI/CD integrations. Keys are shown once — store them securely.</p>

          {newKeyValue && (
            <div className="rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-3 space-y-2">
              <p className="text-xs font-medium text-green-800 dark:text-green-300">New key created — copy it now, it won't be shown again:</p>
              <div className="flex gap-2 items-center">
                <code className="flex-1 font-mono text-xs bg-white dark:bg-black/20 px-2 py-1 rounded border truncate">{newKeyValue}</code>
                <Button size="sm" variant="outline" onClick={() => { navigator.clipboard.writeText(newKeyValue); toast("Copied", "success"); }}>Copy</Button>
              </div>
              <Button size="sm" variant="ghost" className="text-xs" onClick={() => setNewKeyValue(null)}>Dismiss</Button>
            </div>
          )}

          {keysLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm"><Loader2 className="h-4 w-4 animate-spin" /> Loading…</div>
          ) : apiKeys && apiKeys.length > 0 ? (
            <div className="space-y-2">
              {apiKeys.map((k) => (
                <div key={k.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
                  <div>
                    <span className="font-medium">{k.name}</span>
                    <span className="text-muted-foreground ml-2 font-mono text-xs">{k.prefix}…</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground hidden sm:inline">
                      {k.last_used_at ? `Used ${new Date(k.last_used_at).toLocaleDateString()}` : "Never used"}
                    </span>
                    <Button variant="ghost" size="icon" aria-label="Revoke key" className="h-7 w-7 text-red-500 hover:text-red-700" onClick={() => handleDeleteKey(k.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No API keys yet.</p>
          )}

          <form onSubmit={handleCreateKey} className="flex gap-2">
            <Input
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g. github-actions)"
              className="flex-1 text-sm"
            />
            <Button type="submit" size="sm" aria-label="Create API key" disabled={createKey.isPending || !newKeyName.trim()}>
              {createKey.isPending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Plus className="h-4 w-4" aria-hidden />}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-red-200 dark:border-red-900">
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-red-600">Danger Zone</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">Permanently delete your account and all associated data. This cannot be undone.</p>
          {!deleteConfirm ? (
            <Button variant="outline" size="sm" className="border-red-300 text-red-600 hover:bg-red-50" onClick={() => setDeleteConfirm(true)}>
              Delete my account
            </Button>
          ) : (
            <div className="space-y-2">
              <p className="text-sm font-medium text-red-600">Are you sure? This is irreversible.</p>
              <div className="flex gap-2">
                <Button variant="destructive" size="sm" onClick={handleDeleteAccount}>Yes, delete everything</Button>
                <Button variant="outline" size="sm" onClick={() => setDeleteConfirm(false)}>Cancel</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="text-xs text-muted-foreground text-center pt-2">
        ACR-QA v5.0.0b1 · Phase A complete
      </div>
    </div>
  );
}
