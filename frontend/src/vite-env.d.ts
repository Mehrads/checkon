/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  /** The site's public address, for canonical links, link previews, the sitemap and robots.txt */
  readonly VITE_SITE_URL?: string
  /** Shown beside the contact form when set */
  readonly VITE_CONTACT_EMAIL?: string
  /** Umami Cloud website id: page counts only when set */
  readonly VITE_UMAMI_WEBSITE_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
