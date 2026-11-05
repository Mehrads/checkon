import { createFileRoute } from "@tanstack/react-router"
import { useEffect } from "react"
import { Checker } from "@/components/Check/Checker"
import { accountNote } from "@/components/Check/labels"
import { JsonLd, ORGANIZATION } from "@/components/Site/JsonLd"
import {
  ContactSection,
  Faq,
  ForAgencies,
  HeroIntro,
  HowItWorks,
  OpenSource,
  QUESTIONS,
  SampleHint,
  SiteFooter,
  SiteHeader,
} from "@/components/Site/Landing"
import { SampleAudit } from "@/components/Site/SampleAudit"
import { SampleReport } from "@/components/Site/SampleReport"
import { isLoggedIn } from "@/hooks/useAuth"
import { useWorkspaces } from "@/hooks/useWorkspace"
import { loadAnalytics } from "@/lib/analytics"
import { pageHead, SITE } from "@/lib/seo"

const DESCRIPTION =
  "See which lines of a job posting don't meet Ontario's job posting rules, with the source and the smallest fix. For recruiters and HR teams. Free once a week."

export const Route = createFileRoute("/check")({
  component: CheckPage,
  head: () =>
    pageHead({
      path: "/check",
      title: "CheckON: Ontario job posting compliance check in one click",
      description: DESCRIPTION,
    }),
})

/** What search engines read about CheckON: the organisation, the site, the product (free), the FAQ. */
const STRUCTURED = {
  "@graph": [
    ORGANIZATION,
    {
      "@type": "WebSite",
      "@id": `${SITE}/#website`,
      name: "CheckON",
      url: `${SITE}/check`,
      publisher: { "@id": `${SITE}/#organization` },
    },
    {
      "@type": "SoftwareApplication",
      name: "CheckON",
      url: `${SITE}/check`,
      description: DESCRIPTION,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      publisher: { "@id": `${SITE}/#organization` },
      license: "https://www.apache.org/licenses/LICENSE-2.0",
      offers: { "@type": "Offer", price: 0, priceCurrency: "CAD" },
    },
    {
      "@type": "FAQPage",
      mainEntity: QUESTIONS.map((item) => ({
        "@type": "Question",
        name: item.q,
        acceptedAnswer: { "@type": "Answer", text: item.a },
      })),
    },
  ],
}

function CheckPage() {
  useEffect(loadAnalytics, [])
  const signedIn = isLoggedIn() // a signed-in check is saved to the account
  const { current } = useWorkspaces(signedIn)
  return (
    <div className="site landing-glass relative isolate min-h-svh bg-background text-foreground">
      <div className="landing-backdrop" aria-hidden="true" />
      <JsonLd data={STRUCTURED} />
      <SiteHeader />
      <main>
        <Checker
          intro={<HeroIntro />}
          hint={<SampleHint />}
          note={
            signedIn
              ? accountNote(Boolean(current?.archive_postings))
              : undefined
          }
        />
        <div className="landing-panel -mt-6">
          <SampleReport />
          <HowItWorks />
          <SampleAudit />
          <ForAgencies />
          <OpenSource />
          <Faq />
          <ContactSection />
        </div>
      </main>
      <div className="landing-panel mt-3 mb-2 md:mb-6">
        <SiteFooter />
      </div>
    </div>
  )
}
