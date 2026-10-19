import { createFileRoute } from "@tanstack/react-router"

import { Checker } from "@/components/Check/Checker"
import {
  Faq,
  ForTeams,
  HeroIntro,
  HowItWorks,
  Pricing,
  SiteFooter,
  SiteHeader,
  WhatWeCheck,
} from "@/components/Site/Landing"

export const Route = createFileRoute("/check")({
  component: CheckPage,
  head: () => ({
    meta: [
      { title: "PostingCheck: Ontario job posting rules, checked and fixed" },
      {
        name: "description",
        content:
          "Check a job posting against Ontario's 2026 rules on pay, vacancy statements, AI disclosure and Canadian experience, and get a compliant rewrite. Free once a week.",
      },
    ],
  }),
})

function CheckPage() {
  return (
    <div className="min-h-svh bg-background">
      <SiteHeader />
      <main>
        <Checker intro={<HeroIntro />} />
        <HowItWorks />
        <WhatWeCheck />
        <ForTeams />
        <Pricing />
        <Faq />
      </main>
      <SiteFooter />
    </div>
  )
}
