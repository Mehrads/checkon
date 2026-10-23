/** A public page's head for search engines and link previews: title, description, its canonical address, the
 * other languages it's in, and the Open Graph tags with the site's preview image. The public pages are also rendered
 * to HTML at build time (src/prerender.tsx), so these tags are in the page before any script runs. */

export const SITE = "https://checkon.ca"

/** The link preview image (public/og-image.png, made by scripts/og-image.ts). */
const IMAGE = {
  url: `${SITE}/og-image.png`,
  width: "1200",
  height: "630",
  alt: "CheckON: Ontario job posting compliance, in one click",
}

export type Lang = "en" | "fr"

export function pageHead({
  path,
  title,
  description,
  lang = "en",
  alternates = [],
}: {
  path: string
  title: string
  description: string
  lang?: Lang
  /** The same page in other languages, for hreflang links (the page itself is added). */
  alternates?: { lang: Lang; path: string }[]
}) {
  const url = `${SITE}${path}`
  const languages = alternates.length
    ? [{ lang, path }, ...alternates].sort((a, b) =>
        a.lang.localeCompare(b.lang),
      )
    : []
  return {
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:type", content: "website" },
      { property: "og:site_name", content: "CheckON" },
      { property: "og:locale", content: `${lang}_CA` },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:url", content: url },
      { property: "og:image", content: IMAGE.url },
      { property: "og:image:width", content: IMAGE.width },
      { property: "og:image:height", content: IMAGE.height },
      { property: "og:image:alt", content: IMAGE.alt },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:image", content: IMAGE.url },
    ],
    links: [
      { rel: "canonical", href: url },
      ...languages.map((page) => ({
        rel: "alternate",
        hrefLang: `${page.lang}-CA`,
        href: `${SITE}${page.path}`,
      })),
      ...languages
        .filter((page) => page.lang === "en")
        .map((page) => ({
          rel: "alternate",
          hrefLang: "x-default",
          href: `${SITE}${page.path}`,
        })),
    ],
  }
}

/** The account pages and the app's shell: kept out of search results (index.html carries the same tag). */
export const noindex = () => ({
  meta: [{ name: "robots", content: "noindex" }],
})
