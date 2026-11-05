import { SITE } from "@/lib/seo"

/** schema.org data for search engines, in the page (it's rendered into the HTML at build time too). */
export function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      // biome-ignore lint/security/noDangerouslySetInnerHtml: JSON we build ourselves, with "<" escaped
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          "@context": "https://schema.org",
          ...data,
        }).replace(/</g, "\\u003c"),
      }}
    />
  )
}

export const ORGANIZATION = {
  "@type": "Organization",
  "@id": `${SITE}/#organization`,
  name: "CheckON",
  url: `${SITE}/check`,
  logo: `${SITE}/icon-512.png`,
  areaServed: { "@type": "AdministrativeArea", name: "Ontario, Canada" },
}
