import { createFileRoute } from "@tanstack/react-router"
import { useEffect } from "react"

import { Checker } from "@/components/Check/Checker"
import { planNote } from "@/components/Check/labels"
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
import { useBilling } from "@/hooks/useBilling"
import { useWorkspaces } from "@/hooks/useWorkspace"
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
  const { data: billing } = useBilling() // signed in: the plan this check counts toward
  const { current } = useWorkspaces(Boolean(billing?.plan))
  return (
    <ContactProvider>
      <div className="site min-h-svh bg-background text-foreground">
        <SiteHeader />
        <main>
          <Checker
            intro={<HeroIntro />}
            note={
              billing?.plan_name
                ? planNote(
                    billing.plan_name,
                    Boolean(current?.archive_postings),
                  )
                : undefined
            }
          />
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
