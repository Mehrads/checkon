// Where the extension sends checks, and where the website it links to lives. Both are set at build time
// (vite.config.ts): VITE_API_URL, http://localhost:8000 by default, and VITE_SITE_URL, the API's own address by
// default (the API serves the website's build).

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export const SITE = new URL(import.meta.env.VITE_SITE_URL || API_URL).origin
