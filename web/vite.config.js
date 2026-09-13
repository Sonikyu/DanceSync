import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxying /api keeps the browser on one origin, so <video>/<audio> sources
// and the download link need no CORS handling. The API is on :8000 unless
// DANCESYNC_API_URL points somewhere else.
const apiUrl = process.env.DANCESYNC_API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": apiUrl },
  },
});
