import { Navigate, Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { ModeBadge } from "@/components/mode/ModeBadge";
import { CommandPalette } from "@/components/ui/command-palette";
import { Shield, LayoutDashboard, Package, Settings, LogOut, Moon, Sun } from "lucide-react";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";

export function Layout() {
  const { isAuthenticated, logout, user } = useAuth();
  const navigate = useNavigate();
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  if (!isAuthenticated()) return <Navigate to="/login" replace />;

  const navItems = [
    { to: "/", icon: <LayoutDashboard className="h-4 w-4" />, label: "Scans" },
    { to: "/supply-chain", icon: <Package className="h-4 w-4" />, label: "Supply Chain" },
    { to: "/settings", icon: <Settings className="h-4 w-4" />, label: "Settings" },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
        <div className="flex h-14 items-center gap-4 px-4 md:px-6">
          <div className="flex items-center gap-2 font-semibold">
            <Shield className="h-5 w-5 text-primary" />
            <span className="hidden md:inline">ACR-QA</span>
          </div>

          <nav className="flex items-center gap-1 ml-4">
            {navItems.map(({ to, icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`
                }
              >
                {icon}
                <span className="hidden md:inline">{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <ModeBadge />
            <Button variant="ghost" size="icon" aria-label={dark ? "Switch to light mode" : "Switch to dark mode"} onClick={() => setDark(!dark)}>
              {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            {user && <span className="text-xs text-muted-foreground hidden md:inline">{user.email}</span>}
            <Button variant="ghost" size="icon" onClick={() => { logout(); navigate("/login"); }}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 px-4 py-6 md:px-6 md:py-8">
        <Outlet />
      </main>

      <CommandPalette />
    </div>
  );
}
