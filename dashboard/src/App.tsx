import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toast";
import { Layout } from "@/routes/_layout";
import { LoginPage } from "@/routes/auth.login";
import { ScansPage } from "@/routes/index";
import { RunDetailPage } from "@/routes/runs.$id";
import { RunComparePage } from "@/routes/runs.$id.compare";
import { RiskMapPage } from "@/routes/runs.$id.risk-map";
import { ComparePage } from "@/routes/compare";
import { SupplyChainPage } from "@/routes/supply-chain";
import { SettingsPage } from "@/routes/settings";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<Layout />}>
            <Route index element={<ScansPage />} />
            <Route path="/runs/:id" element={<RunDetailPage />} />
            <Route path="/runs/:id/compare" element={<RunComparePage />} />
            <Route path="/runs/:id/risk-map" element={<RiskMapPage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/supply-chain" element={<SupplyChainPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryClientProvider>
  );
}
