import { Link } from "react-router-dom";
import { Shield, Brain, GitBranch, Lock, Zap, Search, BarChart2, Package } from "lucide-react";
import { useEffect, useState } from "react";

interface PublicStats {
  total_runs: number;
  total_findings: number;
  rules: number;
  languages: number;
}

const FEATURES = [
  {
    icon: <Shield size={20} />,
    title: "Multi-Tool SAST",
    desc: "Semgrep, Bandit, Ruff, ESLint, staticcheck — normalized into one canonical finding stream.",
    color: "var(--high)",
  },
  {
    icon: <Brain size={20} />,
    title: "AI Explainer",
    desc: "LLM-grounded explanations with RAG context for every finding. Groq llama3-8b — sub-second.",
    color: "var(--purple)",
  },
  {
    icon: <Zap size={20} />,
    title: "Taint Analysis",
    desc: "Inter-procedural taint tracking from sources to sinks. HTTP inputs → SQL execute paths.",
    color: "var(--blue)",
  },
  {
    icon: <GitBranch size={20} />,
    title: "PR Risk Score",
    desc: "Heuristic risk predictor scores every PR 0–100 with explainable feature contributions.",
    color: "var(--emerald)",
  },
  {
    icon: <Lock size={20} />,
    title: "ECDSA Attestation",
    desc: "Cryptographically signed provenance bundle per scan. SLSA-grade supply chain integrity.",
    color: "var(--purple)",
  },
  {
    icon: <Search size={20} />,
    title: "AI-Code Detector",
    desc: "Statistical classifier detects AI-generated code patterns before they reach production.",
    color: "var(--blue)",
  },
  {
    icon: <BarChart2 size={20} />,
    title: "Time-Travel Analysis",
    desc: "Track when vulnerabilities were introduced and by whom. Regression detection across commits.",
    color: "var(--emerald)",
  },
  {
    icon: <Package size={20} />,
    title: "Supply Chain Risk",
    desc: "SCA + SBOM generation with CVE scoring, maintainer health, and CycloneDX 1.4 export.",
    color: "var(--high)",
  },
];

const STATIC_STATS = [
  { label: "Detection Rules", value: "327" },
  { label: "Languages", value: "5+" },
  { label: "Novel Engines", value: "4" },
  { label: "OWASP Coverage", value: "100%" },
];

export function LandingPage() {
  const [stats, setStats] = useState<PublicStats | null>(null);

  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then((d) => {
        if (d.status === "healthy") {
          setStats({ total_runs: 0, total_findings: 0, rules: 327, languages: 5 });
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", fontFamily: "var(--font)" }}>
      {/* NAV */}
      <nav style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 48px", borderBottom: "1px solid var(--border)",
        background: "rgba(10,10,12,0.90)", backdropFilter: "blur(20px)",
        position: "sticky", top: 0, zIndex: 50,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "var(--gradient)",
            boxShadow: "0 6px 20px -6px rgba(167,139,250,0.55)",
            display: "grid", placeItems: "center", fontSize: 16, flexShrink: 0,
          }}>✦</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15, color: "var(--fg)", letterSpacing: "-0.02em" }}>ACR-QA</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--fg-5)" }}>v5.0.0-b1</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Link to="/login" style={{
            padding: "7px 16px", borderRadius: 7, fontSize: 13,
            color: "var(--fg-3)", border: "1px solid var(--border-2)",
            background: "transparent",
          }}>Sign in</Link>
          <Link to="/register" style={{
            padding: "7px 16px", borderRadius: 7, fontSize: 13,
            color: "#fff", background: "var(--gradient)",
            fontWeight: 600, boxShadow: "0 4px 14px -4px rgba(167,139,250,0.5)",
          }}>Get Started</Link>
        </div>
      </nav>

      {/* HERO */}
      <div style={{ textAlign: "center", padding: "96px 48px 64px", maxWidth: 800, margin: "0 auto" }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8, padding: "5px 14px",
          borderRadius: 20, border: "1px solid rgba(167,139,250,0.3)",
          background: "rgba(167,139,250,0.08)", marginBottom: 28,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--purple)", boxShadow: "0 0 8px var(--purple)" }} />
          <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--purple)" }}>
            Thesis Research Project · KSIU 2026
          </span>
        </div>

        <h1 style={{
          fontSize: "clamp(36px, 6vw, 60px)", fontWeight: 900,
          color: "var(--fg)", lineHeight: 1.05, letterSpacing: "-0.04em",
          margin: "0 0 20px",
        }}>
          Automated Code Review<br />
          <span style={{ background: "var(--gradient)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            &amp; Quality Assurance
          </span>
        </h1>

        <p style={{
          fontSize: 17, color: "var(--fg-3)", lineHeight: 1.7,
          margin: "0 auto 40px", maxWidth: 560,
        }}>
          Multi-engine SAST platform with AI explanations, taint analysis, PR risk scoring,
          and cryptographic attestation — all in one dashboard.
        </p>

        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/register" style={{
            padding: "11px 28px", borderRadius: 8, fontSize: 14, fontWeight: 600,
            color: "#fff", background: "var(--gradient)",
            boxShadow: "0 6px 24px -6px rgba(167,139,250,0.6)",
          }}>
            Start Free →
          </Link>
          <Link to="/login" style={{
            padding: "11px 28px", borderRadius: 8, fontSize: 14,
            color: "var(--fg-2)", border: "1px solid var(--border-2)",
            background: "rgba(255,255,255,0.02)",
          }}>
            Sign In
          </Link>
        </div>
      </div>

      {/* STATS BAR */}
      <div style={{
        display: "flex", justifyContent: "center", gap: 0,
        borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)",
        background: "var(--bg-2)",
      }}>
        {STATIC_STATS.map(({ label, value }, i) => (
          <div key={label} style={{
            padding: "20px 40px", textAlign: "center", flex: 1, maxWidth: 200,
            borderRight: i < STATIC_STATS.length - 1 ? "1px solid var(--border)" : "none",
          }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 24, fontWeight: 700, color: "var(--fg)", marginBottom: 4 }}>
              {stats ? (label === "Detection Rules" ? stats.rules : label === "Languages" ? `${stats.languages}+` : value) : value}
            </div>
            <div style={{ fontSize: 12, color: "var(--fg-4)" }}>{label}</div>
          </div>
        ))}
      </div>

      {/* FEATURES GRID */}
      <div style={{ padding: "80px 48px", maxWidth: 1100, margin: "0 auto" }}>
        <h2 style={{
          textAlign: "center", fontSize: 32, fontWeight: 800, color: "var(--fg)",
          letterSpacing: "-0.03em", marginBottom: 12,
        }}>Everything in one platform</h2>
        <p style={{ textAlign: "center", color: "var(--fg-4)", marginBottom: 52, fontSize: 15 }}>
          Four novel engines not found in commercial SAST tools
        </p>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: 16,
        }}>
          {FEATURES.map(({ icon, title, desc, color }) => (
            <div key={title} style={{
              padding: "22px 20px", borderRadius: 10,
              background: "var(--bg-2)", border: "1px solid var(--border)",
              transition: "border-color 0.15s",
            }}>
              <div style={{
                width: 38, height: 38, borderRadius: 8, display: "grid", placeItems: "center",
                background: `${color}14`, color, marginBottom: 12, flexShrink: 0,
              }}>{icon}</div>
              <div style={{ fontWeight: 600, fontSize: 14, color: "var(--fg)", marginBottom: 6 }}>{title}</div>
              <div style={{ fontSize: 13, color: "var(--fg-4)", lineHeight: 1.6 }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div style={{
        textAlign: "center", padding: "80px 48px",
        borderTop: "1px solid var(--border)",
        background: "var(--bg-2)",
      }}>
        <h2 style={{ fontSize: 28, fontWeight: 800, color: "var(--fg)", marginBottom: 12, letterSpacing: "-0.03em" }}>
          Ready to scan your codebase?
        </h2>
        <p style={{ color: "var(--fg-4)", marginBottom: 32, fontSize: 15 }}>
          Create a free account and run your first scan in minutes.
        </p>
        <Link to="/register" style={{
          display: "inline-block", padding: "12px 32px", borderRadius: 8, fontSize: 15, fontWeight: 600,
          color: "#fff", background: "var(--gradient)",
          boxShadow: "0 8px 28px -8px rgba(167,139,250,0.6)",
        }}>
          Create Account →
        </Link>
      </div>

      {/* FOOTER */}
      <footer style={{
        textAlign: "center", padding: "24px 48px",
        borderTop: "1px solid var(--border)",
        fontSize: 12, color: "var(--fg-5)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <span>ACR-QA v5.0.0-b1 · KSIU Computer Science 2026</span>
        <div style={{ display: "flex", gap: 20 }}>
          <Link to="/login" style={{ color: "var(--fg-5)" }}>Sign In</Link>
          <Link to="/register" style={{ color: "var(--fg-5)" }}>Register</Link>
        </div>
      </footer>
    </div>
  );
}
