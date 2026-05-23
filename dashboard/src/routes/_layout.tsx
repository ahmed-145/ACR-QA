import { useState, useEffect } from "react";
import { Navigate, Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { ModeBadge } from "@/components/mode/ModeBadge";
import { CommandPalette } from "@/components/ui/command-palette";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { ThreatLevel } from "@/components/ui/ThreatLevel";
import { AlertBanner } from "@/components/ui/AlertBanner";
import { ShortcutsModal } from "@/components/ui/ShortcutsModal";
import { useDensityEffect } from "@/lib/useDensity";
import { useRuns, useInbox } from "@/lib/queries";
import {
  LayoutDashboard, Package, Settings, LogOut, GitCompare,
  Brain, BarChart2, Languages, Search, DollarSign, GitBranch,
  Shield, List, Home, Inbox, Map, Terminal, Sun, Moon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { setLanguage } from "@/lib/i18n";

export function Layout() {
  const { isAuthenticated, logout, user } = useAuth();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const isRtl = i18n.language === "ar";
  useDensityEffect();
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains("dark"));
  function toggleTheme() {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("acrqa-theme", next ? "dark" : "light");
  }
  const { data: runsData } = useRuns(5);
  const latestCompleted = runsData?.runs?.find((r) => r.status === "completed");
  const highCount = latestCompleted?.high_count ?? 0;
  const { data: inboxData } = useInbox();
  const inboxCount = inboxData?.total ?? 0;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "?") { e.preventDefault(); setShortcutsOpen((v) => !v); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!isAuthenticated()) return <Navigate to="/login" replace />;

  const navSections = [
    {
      label: "Analysis",
      items: [
        { to: "/inbox", icon: <Inbox size={15} aria-hidden />, label: "Inbox", count: inboxCount || undefined },
        { to: "/overview", icon: <Home size={15} aria-hidden />, label: "Overview" },
        { to: "/scans", icon: <LayoutDashboard size={15} aria-hidden />, label: t("nav.scans") },
        { to: "/findings", icon: <Search size={15} aria-hidden />, label: "All Findings" },
        { to: "/vulnerabilities", icon: <Shield size={15} aria-hidden />, label: "Vulnerabilities" },
        { to: "/repos", icon: <GitBranch size={15} aria-hidden />, label: "Repositories" },
        { to: "/compare", icon: <GitCompare size={15} aria-hidden />, label: "Compare" },
        { to: "/supply-chain", icon: <Package size={15} aria-hidden />, label: t("nav.supplyChain") },
      ],
    },
    {
      label: "Intelligence",
      items: [
        { to: "/fleet",      icon: <Map size={15} aria-hidden />,       label: "Fleet" },
        { to: "/workbench",  icon: <Terminal size={15} aria-hidden />,  label: "Workbench" },
        { to: "/analytics",  icon: <BarChart2 size={15} aria-hidden />, label: "Analytics" },
        { to: "/ai-detect",  icon: <Brain size={15} aria-hidden />,     label: "AI Detector" },
        { to: "/cost",       icon: <DollarSign size={15} aria-hidden />, label: "Cost & ROI" },
      ],
    },
    {
      label: "Config",
      items: [
        { to: "/rules", icon: <List size={15} aria-hidden />, label: "Rules Browser" },
        { to: "/policy", icon: <Shield size={15} aria-hidden />, label: "Policy" },
        { to: "/settings", icon: <Settings size={15} aria-hidden />, label: t("nav.settings") },
      ],
    },
  ];

  const emailDisplay = user?.email ?? "user@acrqa";
  const initials = emailDisplay.slice(0, 2).toUpperCase();
  const username = emailDisplay.split("@")[0];

  return (
    <div className="app" dir={isRtl ? "rtl" : "ltr"}>
      {/* SIDEBAR */}
      <aside className="sidebar" role="navigation" aria-label="Main navigation">
        {/* Brand */}
        <div className="brand-row">
          <div className="logo" aria-hidden>✦</div>
          <div className="wm-stack">
            <span className="wm">ACR-QA</span>
            <span className="ver">v5.0.0-b1</span>
          </div>
        </div>

        {/* Nav sections */}
        {navSections.map((section) => (
          <div key={section.label}>
            <div className="nav-section">{section.label}</div>
            {section.items.map(({ to, icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => `nav-item${isActive ? " on" : ""}`}
              >
                <span className="ico">{icon}</span>
                {label}
              </NavLink>
            ))}
          </div>
        ))}

        {/* Footer */}
        <div className="sb-footer">
          <div className="sb-status">
            <span className="led" aria-hidden />
            API connected
            <span style={{ marginLeft: "auto" }}>
              <ThreatLevel highCount={highCount} />
            </span>
          </div>
          <div className="sb-acct">
            <div className="avatar" aria-hidden>{initials}</div>
            <div className="stack">
              <span className="nm">{username}</span>
              <span className="sub">{user?.role ?? "analyst"}</span>
            </div>
          </div>

          {/* Footer actions */}
          <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
            <button
              className="btn-icon"
              style={{ flex: 1 }}
              aria-label={isRtl ? "Switch to English" : "Switch to Arabic (عربي)"}
              onClick={() => setLanguage(isRtl ? "en" : "ar")}
              title={isRtl ? "English" : "عربي"}
            >
              <Languages size={14} aria-hidden />
            </button>
            <button
              className="btn-icon"
              style={{ flex: 1 }}
              aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
              onClick={toggleTheme}
              title={isDark ? "Light mode" : "Dark mode"}
            >
              {isDark ? <Sun size={14} aria-hidden /> : <Moon size={14} aria-hidden />}
            </button>
            <ModeBadge />
            <button
              className="btn-icon"
              style={{ flex: 1 }}
              aria-label="Sign out"
              onClick={() => { logout(); navigate("/login"); }}
            >
              <LogOut size={14} aria-hidden />
            </button>
          </div>
        </div>
      </aside>

      {/* MAIN COLUMN */}
      <div className="main">
        <AlertBanner highCount={highCount} runId={latestCompleted?.id} />
        <main id="main-content" role="main">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>

      <CommandPalette />
      <ShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
}
