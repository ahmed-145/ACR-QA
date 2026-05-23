import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, loginApi } from "@/lib/auth";
import { Shield } from "lucide-react";

export function LoginPage() {
  const [email, setEmail] = useState("admin@acrqa.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { setToken } = useAuth();
  const navigate = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { access_token, user } = await loginApi(email, password);
      setToken(access_token, user);
      navigate("/");
    } catch {
      setError("Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <div className="logo" aria-hidden><Shield size={14} /></div>
          <div className="wm-stack">
            <h1 className="wm" style={{ margin: 0 }}>ACR-QA</h1>
            <span className="ver">v5.0.0-b1</span>
          </div>
        </div>

        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: "var(--fg)", marginBottom: 4 }}>Sign in</div>
          <div style={{ fontSize: 13, color: "var(--fg-4)" }}>Automated Code Review &amp; Quality Assurance</div>
        </div>

        <form onSubmit={submit} className="login-fields">
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="inp"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              className="inp"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="changeme123!"
              autoComplete="current-password"
            />
          </div>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="btn-prim" style={{ width: "100%", justifyContent: "center", height: 40 }} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : null}
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
