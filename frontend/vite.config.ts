import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

// https://vitejs.dev/config/
// `--mode prerender` builds src/prerender.tsx for scripts/prerender.ts: one bundle, no code splitting, and the CSS
// and font imports compiled away.
export default defineConfig(({ mode }) => ({
  ssr: mode === "prerender" ? { noExternal: true } : undefined,
  build: {
    outDir: "../backend/app/frontend",
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  plugins: [
    tanstackRouter({
      target: "react",
      autoCodeSplitting: mode !== "prerender",
    }),
    react(),
    tailwindcss(),
  ],
}))
