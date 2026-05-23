import { useEffect } from "react";
import { create } from "zustand";
import { persist } from "zustand/middleware";

type Density = "comfortable" | "compact";

interface DensityStore {
  density: Density;
  toggle: () => void;
  set: (d: Density) => void;
}

export const useDensity = create<DensityStore>()(
  persist(
    (set) => ({
      density: "comfortable",
      toggle: () => set((s) => ({ density: s.density === "comfortable" ? "compact" : "comfortable" })),
      set: (density) => set({ density }),
    }),
    { name: "acrqa_density" }
  )
);

export function useDensityEffect() {
  const density = useDensity((s) => s.density);
  useEffect(() => {
    document.documentElement.setAttribute("data-density", density);
  }, [density]);
}
