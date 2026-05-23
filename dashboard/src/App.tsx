import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toast";
import { Layout } from "@/routes/_layout";
import { LandingPage } from "@/routes/landing";
import { LoginPage } from "@/routes/auth.login";
import { RegisterPage } from "@/routes/auth.register";
import { useAuth } from "@/lib/auth";

// Route-level code splitting — heavy pages are lazy-loaded
const ScansPage       = lazy(() => import("@/routes/index").then((m) => ({ default: m.ScansPage })));
const OverviewPage    = lazy(() => import("@/routes/overview").then((m) => ({ default: m.OverviewPage })));
const RunDetailPage   = lazy(() => import("@/routes/runs.$id").then((m) => ({ default: m.RunDetailPage })));
const RunComparePage  = lazy(() => import("@/routes/runs.$id.compare").then((m) => ({ default: m.RunComparePage })));
const RiskMapPage     = lazy(() => import("@/routes/runs.$id.risk-map").then((m) => ({ default: m.RiskMapPage })));
const ComparePage     = lazy(() => import("@/routes/compare").then((m) => ({ default: m.ComparePage })));
const SupplyChainPage = lazy(() => import("@/routes/supply-chain").then((m) => ({ default: m.SupplyChainPage })));
const SettingsPage    = lazy(() => import("@/routes/settings").then((m) => ({ default: m.SettingsPage })));
const AnalyticsPage   = lazy(() => import("@/routes/analytics").then((m) => ({ default: m.AnalyticsPage })));
const AIDetectPage    = lazy(() => import("@/routes/ai-detect").then((m) => ({ default: m.AIDetectPage })));
const FindingsPage    = lazy(() => import("@/routes/findings").then((m) => ({ default: m.FindingsPage })));
const CostPage        = lazy(() => import("@/routes/cost").then((m) => ({ default: m.CostPage })));
const ReposPage       = lazy(() => import("@/routes/repos").then((m) => ({ default: m.ReposPage })));
const RulesPage       = lazy(() => import("@/routes/rules").then((m) => ({ default: m.RulesPage })));
const PolicyPage      = lazy(() => import("@/routes/policy").then((m) => ({ default: m.PolicyPage })));
const VulnDetailPage  = lazy(() => import("@/routes/vuln.$shortId").then((m) => ({ default: m.VulnDetailPage })));
const InboxPage       = lazy(() => import("@/routes/inbox").then((m) => ({ default: m.InboxPage })));
const FleetPage       = lazy(() => import("@/routes/fleet").then((m) => ({ default: m.FleetPage })));
const WorkbenchPage   = lazy(() => import("@/routes/workbench").then((m) => ({ default: m.WorkbenchPage })));
const TrustPage            = lazy(() => import("@/routes/trust.$repoName").then((m) => ({ default: m.TrustPage })));
const VulnerabilitiesPage  = lazy(() => import("@/routes/vulnerabilities").then((m) => ({ default: m.VulnerabilitiesPage })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

function PageFallback() {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh" }}>
      <span className="spinner" style={{ width: 24, height: 24 }} aria-label="Loading page" />
    </div>
  );
}

function HomeRedirect() {
  const { isAuthenticated } = useAuth();
  return isAuthenticated() ? <Navigate to="/inbox" replace /> : <LandingPage />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/trust/:repoName" element={<Suspense fallback={<PageFallback />}><TrustPage /></Suspense>} />
          <Route element={<Layout />}>
            <Route path="/overview"          element={<Suspense fallback={<PageFallback />}><OverviewPage /></Suspense>} />
            <Route path="/scans"             element={<Suspense fallback={<PageFallback />}><ScansPage /></Suspense>} />
            <Route path="/runs/:id"          element={<Suspense fallback={<PageFallback />}><RunDetailPage /></Suspense>} />
            <Route path="/runs/:id/compare"  element={<Suspense fallback={<PageFallback />}><RunComparePage /></Suspense>} />
            <Route path="/runs/:id/risk-map" element={<Suspense fallback={<PageFallback />}><RiskMapPage /></Suspense>} />
            <Route path="/compare"           element={<Suspense fallback={<PageFallback />}><ComparePage /></Suspense>} />
            <Route path="/supply-chain"      element={<Suspense fallback={<PageFallback />}><SupplyChainPage /></Suspense>} />
            <Route path="/settings"          element={<Suspense fallback={<PageFallback />}><SettingsPage /></Suspense>} />
            <Route path="/analytics"         element={<Suspense fallback={<PageFallback />}><AnalyticsPage /></Suspense>} />
            <Route path="/ai-detect"         element={<Suspense fallback={<PageFallback />}><AIDetectPage /></Suspense>} />
            <Route path="/findings"          element={<Suspense fallback={<PageFallback />}><FindingsPage /></Suspense>} />
            <Route path="/cost"              element={<Suspense fallback={<PageFallback />}><CostPage /></Suspense>} />
            <Route path="/repos"             element={<Suspense fallback={<PageFallback />}><ReposPage /></Suspense>} />
            <Route path="/rules"             element={<Suspense fallback={<PageFallback />}><RulesPage /></Suspense>} />
            <Route path="/policy"            element={<Suspense fallback={<PageFallback />}><PolicyPage /></Suspense>} />
            <Route path="/vulnerabilities"   element={<Suspense fallback={<PageFallback />}><VulnerabilitiesPage /></Suspense>} />
            <Route path="/vuln/:shortId"     element={<Suspense fallback={<PageFallback />}><VulnDetailPage /></Suspense>} />
            <Route path="/inbox"             element={<Suspense fallback={<PageFallback />}><InboxPage /></Suspense>} />
            <Route path="/fleet"             element={<Suspense fallback={<PageFallback />}><FleetPage /></Suspense>} />
            <Route path="/workbench"         element={<Suspense fallback={<PageFallback />}><WorkbenchPage /></Suspense>} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryClientProvider>
  );
}
