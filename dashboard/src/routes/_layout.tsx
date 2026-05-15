import { Navigate, Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { ModeBadge } from "@/components/mode/ModeBadge";
import { CommandPalette } from "@/components/ui/command-palette";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { Shield, LayoutDashboard, Package, Settings, LogOut, Moon, Sun, Languages } from "lucide-react";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";
import { setLanguage } from "@/lib/i18n";

export function Layout() {
  const { isAuthenticated, logout, user } = useAuth();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  const isRtl = i18n.language === "ar";

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  if (!isAuthenticated()) return <Navigate to="/login" replace />;

  const navItems = [
    { to: "/", icon: <LayoutDashboard className="h-4 w-4" aria-hidden />, label: t("nav.scans") },
    { to: "/supply-chain", icon: <Package className="h-4 w-4" aria-hidden />, label: t("nav.supplyChain") },
    { to: "/settings", icon: <Settings className="h-4 w-4" aria-hidden />, label: t("nav.settings") },
  ];

  function toggleLanguage() {
    setLanguage(isRtl ? "en" : "ar");
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur" role="banner">
        <div className="flex h-14 items-center gap-4 px-4 md:px-6">
          <div className="flex items-center gap-2 font-semibold" aria-label="ACR-QA home">
            <Shield className="h-5 w-5 text-primary" aria-hidden />
            <span className="hidden md:inline">ACR-QA</span>
          </div>

          <nav aria-label="Main navigation" className="flex items-center gap-1 ml-4">
            {navItems.map(({ to, icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`
                }
                aria-current={undefined}
              >
                {icon}
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <ModeBadge />

            {/* Language toggle */}
            <Button
              variant="ghost"
              size="icon"
              aria-label={isRtl ? "Switch to English" : "Switch to Arabic (عربي)"}
              onClick={toggleLanguage}
              title={isRtl ? "English" : "عربي"}
            >
              <Languages className="h-4 w-4" aria-hidden />
            </Button>

            <Button
              variant="ghost"
              size="icon"
              aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
              onClick={() => setDark(!dark)}
            >
              {dark ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
            </Button>

            {user && (
              <span className="text-xs text-muted-foreground hidden md:inline" aria-label={`Signed in as ${user.email}`}>
                {user.email}
              </span>
            )}

            <Button
              variant="ghost"
              size="icon"
              aria-label="Sign out"
              onClick={() => { logout(); navigate("/login"); }}
            >
              <LogOut className="h-4 w-4" aria-hidden />
            </Button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main id="main-content" className="flex-1 px-4 py-6 md:px-6 md:py-8" role="main">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>

      <CommandPalette />
    </div>
  );
}
