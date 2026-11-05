/** After the build: write each public page as HTML next to index.html (src/prerender.tsx renders them). The page's
 * title, description, canonical link and Open Graph tags go into the head, in place of index.html's (which also
 * keep the app's own pages out of search results), marked so the app removes them when it starts (its routes render
 * their own); its content goes inside #root, marked so index.html can hide it from someone signed in until the app
 * has rendered. Then 404.html, which the API sends for unknown addresses, the sitemap of the public pages, and
 * robots.txt pointing at it. Both use the site's address from VITE_SITE_URL (src/lib/seo.ts). */

import { readFile, writeFile } from "node:fs/promises"
import { join } from "node:path"

// @ts-expect-error: built by `vite build --ssr src/prerender.tsx --outDir .prerender`
import { NOT_FOUND, PAGES, render, SITE } from "../.prerender/prerender.js"

const OUT = join(import.meta.dir, "..", "..", "backend", "app", "frontend")
const HEAD_TAG = /<(title)>[^<]*<\/title>|<(meta|link)\b[^>]*\/?>/g
const STATIC_TITLE = /<title data-static-head>[^<]*<\/title>/
const STATIC_META = /<meta\s+data-static-head[^>]*>/g

const shell = await readFile(join(OUT, "index.html"), "utf8")
const withBody = (page: string, body: string) =>
  page.replace(
    '<div id="root"></div>',
    `<div id="root"><div data-prerendered>${body}</div></div>`,
  )

for (const [path, file] of Object.entries(PAGES as Record<string, string>)) {
  const rendered: string = await render(path)
  // React writes the route's <title>, <meta> and <link> tags where they're rendered; they belong in the head
  const head = rendered.match(HEAD_TAG) ?? []
  const body = rendered.replace(HEAD_TAG, "")
  if (!head.some((tag) => tag.startsWith("<title>")) || body.length < 1000) {
    throw new Error(`Prerendering ${path} produced no page`)
  }
  const marked = head.map((tag) =>
    tag.replace(/^<(\w+)/, "<$1 data-static-head"),
  )
  const page = withBody(
    shell
      .replace(STATIC_TITLE, "")
      .replace(STATIC_META, "")
      .replace("</head>", `${marked.join("")}</head>`)
      .replace(
        '<html lang="en">',
        `<html lang="${path.startsWith("/fr/") ? "fr-CA" : "en"}">`,
      ),
    body,
  )
  await writeFile(join(OUT, file), page)
  console.log(
    `prerendered ${path} -> ${file} (${body.length.toLocaleString()} characters)`,
  )
}

// The shell's noindex stays; only the title and description change
const notFound = (await render(NOT_FOUND)).replace(HEAD_TAG, "")
if (!notFound.includes('data-testid="not-found"')) {
  throw new Error("Prerendering the not-found page produced no page")
}
await writeFile(
  join(OUT, "404.html"),
  withBody(
    shell
      .replace(
        STATIC_TITLE,
        "<title data-static-head>Page not found | CheckON</title>",
      )
      .replace(/<meta\s+data-static-head\s+name="description"[^>]*>/, ""),
    notFound,
  ),
)
console.log("prerendered the not-found page -> 404.html")

const urls = Object.keys(PAGES as Record<string, string>).map(
  (path) => `  <url><loc>${SITE}${path}</loc></url>`,
)
await writeFile(
  join(OUT, "sitemap.xml"),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join("\n")}\n</urlset>\n`,
)
console.log(`sitemap.xml: ${urls.length} pages`)

await writeFile(
  join(OUT, "robots.txt"),
  `User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: ${SITE}/sitemap.xml\n`,
)
console.log(`robots.txt: sitemap at ${SITE}/sitemap.xml`)
