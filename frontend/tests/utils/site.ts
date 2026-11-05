import path from "node:path"
import { fileURLToPath } from "node:url"
import dotenv from "dotenv"

// The site's address the pages were built with: VITE_SITE_URL from the environment or frontend/.env, as
// src/lib/seo.ts reads it for canonical links and link previews.
dotenv.config({
  path: path.join(path.dirname(fileURLToPath(import.meta.url)), "../../.env"),
})

export const SITE = (
  process.env.VITE_SITE_URL || "http://localhost:5173"
).replace(/\/+$/, "")
