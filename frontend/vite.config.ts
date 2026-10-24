import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// В разработке (npm run dev) запросы /api проксируются на бэкенд, как это делает nginx в Docker
export default defineConfig({
  plugins: [react()],
  build: { chunkSizeWarningLimit: 1000 },
  server: {
    port: 5173,
    proxy: { "/api": process.env.VITE_API_PROXY ?? "http://localhost:8000" },
  },
});
