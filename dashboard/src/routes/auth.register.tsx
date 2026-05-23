import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setToken } = useAuth();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirm) { setError("Passwords do not match"); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      const res = await fetch("/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Registration failed");

      // Auto-login after register
      const loginRes = await fetch("/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const loginData = await loginRes.json();
      if (!loginRes.ok) throw new Error("Registered but login failed — try signing in manually");
      setToken(loginData.access_token, loginData.user ?? { email, role: "analyst" });
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "var(--gradient)",
            boxShadow: "0 8px 20px -8px rgba(167,139,250,0.6)",
            display: "grid", placeItems: "center",
            fontSize: 18, margin: "0 auto 14px",
          }}>✦</div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--fg)", margin: "0 0 6px", letterSpacing: "-0.03em" }}>
            Create account
          </h1>
          <p style={{ fontSize: 13, color: "var(--fg-4)", margin: 0 }}>
            ACR-QA — Automated Code Review &amp; Quality Assurance
          </p>
        </div>

        {error && (
          <div style={{
            padding: "10px 14px", borderRadius: 7, marginBottom: 16,
            background: "rgba(239,68,68,0.10)", border: "1px solid rgba(239,68,68,0.25)",
            color: "var(--high-fg)", fontSize: 13,
          }}>{error}</div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "var(--fg-4)", marginBottom: 6 }}>
              Email address
            </label>
            <input
              className="inp"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "var(--fg-4)", marginBottom: 6 }}>
              Password
            </label>
            <input
              className="inp"
              type="password"
              placeholder="Minimum 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: "var(--fg-4)", marginBottom: 6 }}>
              Confirm password
            </label>
            <input
              className="inp"
              type="password"
              placeholder="Repeat password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>
          <button className="btn-prim" type="submit" disabled={loading} style={{ marginTop: 4 }}>
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: 13, color: "var(--fg-4)", marginTop: 20, marginBottom: 0 }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "var(--purple)", fontWeight: 500 }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}
