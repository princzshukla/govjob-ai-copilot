import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // 5173 is allow-listed in the backend CORS_ORIGINS — don't change it without
    // adding the new origin there too.
    port: 5173,
    host: "127.0.0.1",
    strictPort: true,
  },
  build: {
    target: "es2022",
    cssMinify: "lightningcss",
  },
});
