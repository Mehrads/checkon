/** A public page's head for search engines and link previews: title, description, its canonical address and the
 * Open Graph tags. The public pages are also rendered to HTML at build time (src/prerender.tsx), so these tags are
 * in the page before any script runs. */

export const SITE = "https://checkon.ca"

export function pageHead({
  path,
  title,
  description,
}: {
  path: string
  title: string
  description: string
}) {
  const url = `${SITE}${path}`
  return {
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:type", content: "website" },
      { property: "og:site_name", content: "CheckON" },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:url", content: url },
      { name: "twitter:card", content: "summary" },
    ],
    links: [{ rel: "canonical", href: url }],
  }
}
