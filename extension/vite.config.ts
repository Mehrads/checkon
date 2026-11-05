import { readFileSync } from "node:fs"
import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig, type Plugin } from "vite"

const dir = import.meta.dirname
const pkg = JSON.parse(readFileSync(path.join(dir, "package.json"), "utf8"))

// The API the extension calls: your own CheckON server, set when you build (extension/README.md). The local
// backend unless VITE_API_URL says otherwise. VITE_SITE_URL is where its website lives, for the panel's links
// (log-in help, the company profile, the archive, privacy); by default the API's own address, which serves it.
const API_URL = process.env.VITE_API_URL || "http://localhost:8000"
const SITE_URL = process.env.VITE_SITE_URL || API_URL

const ICONS = {
  "16": "icons/icon-16.png",
  "32": "icons/icon-32.png",
  "48": "icons/icon-48.png",
  "128": "icons/icon-128.png",
}

/** manifest.json, written at build time. `--mode unpacked` adds a public key so the ID stays
 * lfepfedddcabkigmmhbhacdllgljpdbe when loaded unpacked; the Chrome Web Store build leaves it out. */
function manifest(mode: string): Plugin {
  const key =
    mode === "unpacked"
      ? readFileSync(path.join(dir, "unpacked-public-key.txt"), "utf8").trim()
      : undefined
  return {
    name: "checkon-manifest",
    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "manifest.json",
        source: JSON.stringify(
          {
            manifest_version: 3,
            name: "CheckON: Ontario job posting check",
            short_name: "CheckON",
            version: pkg.version,
            description:
              "Ontario compliance check for your job postings, in one click. Reads the posting on the page and writes the fixes you approve back.",
            minimum_chrome_version: "116",
            icons: ICONS,
            action: {
              default_title: "Check this posting with CheckON",
              default_icon: ICONS,
            },
            side_panel: { default_path: "sidepanel.html" },
            background: { service_worker: "background.js", type: "module" },
            permissions: [
              "sidePanel",
              "activeTab",
              "scripting",
              "contextMenus",
              "storage",
            ],
            host_permissions: [`${new URL(API_URL).origin}/*`],
            ...(key ? { key } : {}),
          },
          null,
          2,
        ),
      })
    },
  }
}

export default defineConfig(({ mode }) => ({
  base: "/",
  resolve: {
    alias: {
      // The side panel reuses the website's check components and API client.
      "@": path.resolve(dir, "../frontend/src"),
    },
  },
  define: {
    "import.meta.env.VITE_API_URL": JSON.stringify(API_URL),
    "import.meta.env.VITE_SITE_URL": JSON.stringify(SITE_URL),
  },
  plugins: [react(), tailwindcss(), manifest(mode)],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        sidepanel: path.resolve(dir, "sidepanel.html"),
        background: path.resolve(dir, "src/background.ts"),
        // Injected into the posting's page for the on-page mode: one plain script, no imports.
        overlay: path.resolve(dir, "src/overlay.ts"),
      },
      output: {
        entryFileNames: (chunk) =>
          chunk.name === "background" || chunk.name === "overlay"
            ? `${chunk.name}.js`
            : "assets/[name]-[hash].js",
      },
    },
  },
}))
