import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // 5173 is allow-listed in the backend CORS_ORIGINS. Use the SAME hostname
    // the API uses — the session cookie is SameSite=Lax, and 127.0.0.1 vs
    // localhost count as different sites, so cookies would never be sent.
    port: 5173,
    host: "localhost",
    strictPort: true,
  },
  build: {
    target: "es2022",
    cssMinify: "lightningcss",
    rollupOptions: {
      output: {
        // Keep the rarely-used tabs in their own chunks even though they are
        // statically imported (SSR needs them eagerly).
        manualChunks(id) {
          if (id.includes("components/rozgar/DocumentResizer")) return "resizer";
          if (id.includes("views/directions/rozgar-pages")) return "rozgar-pages";
          if (id.includes("components/rozgar/AccountModal")) return "account-modal";
        },
      },
    },
  },
});
