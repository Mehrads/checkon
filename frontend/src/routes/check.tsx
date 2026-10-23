import { createFileRoute } from "@tanstack/react-router"
import { useEffect } from "react"

import { Checker } from "@/components/Check/Checker"
import { ContactProvider } from "@/components/Site/Contact"
import {
  ContactSection,
  Faq,
  ForTeams,
  HeroIntro,
  HowItWorks,
  NextPosting,
  Pricing,
  SampleFix,
  SiteFooter,
  SiteHeader,
  WhatYouGet,
} from "@/components/Site/Landing"
import { SampleAudit } from "@/components/Site/SampleAudit"
import { isLoggedIn } from "@/hooks/useAuth"
import { loadAnalytics } from "@/lib/analytics"

export const Route = createFileRoute("/check")({
  component: CheckPage,
  head: () => ({
    meta: [
      { title: "CheckON: Ontario job posting compliance check in one click" },
      {
        name: "description",
        content:
          "Check your job posting for Ontario compliance in one click and get a compliant rewrite you approve. Free once a week.",
      },
    ],
  }),
})

function CheckPage() {
  useEffect(loadAnalytics, [])
  return (
    <ContactProvider>
      <div className="site min-h-svh bg-background text-foreground">
        <SiteHeader />
        <main>
          <Checker
            intro={<HeroIntro />}
            note={
              isLoggedIn()
                ? "You're logged in: on a plan, this check counts toward it, and we keep its date, job title and result for your history, never the posting."
                : undefined
            }
          />
          <WhatYouGet />
          <SampleFix />
          <HowItWorks />
          <ForTeams />
          <SampleAudit />
          <Pricing />
          <Faq />
          <NextPosting />
          <ContactSection />
        </main>
        <SiteFooter />
      </div>
    </ContactProvider>
  )
}
