import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxies /api to the local FastAPI backend on port 5050.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:5050",
      "/health": "http://localhost:5050",
    },
  },
});
