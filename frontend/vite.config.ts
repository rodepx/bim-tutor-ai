/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // src/rules.ts importa ../data/rules.json (fuente única de reglas del repo).
    fs: { allow: [".."] },
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "node",
  },
});
