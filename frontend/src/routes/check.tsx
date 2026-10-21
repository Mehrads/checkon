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
          <Checker intro={<HeroIntro />} />
          <WhatYouGet />
          <SampleFix />
          <HowItWorks />
          <ForTeams />
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
