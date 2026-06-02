/// <reference types="vitest" />
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/v1": { target: "http://localhost:8002", changeOrigin: true },
      "/health": { target: "http://localhost:8002", changeOrigin: true },
      "/celery": { target: "http://localhost:8002", changeOrigin: true },
      "/openapi.json": { target: "http://localhost:8002", changeOrigin: true },
    },
  },
  build: {
    outDir: "../FRONTEND/static/dashboard",
    emptyOutDir: true,
  },
  test: {
    globals: true,
    environment: "happy-dom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/test/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["e2e/**", "node_modules/**"],
  },
});
