import { createFileRoute } from "@tanstack/react-router"

import { Checker } from "@/components/Check/Checker"
import { ContactProvider } from "@/components/Site/Contact"
import {
  ContactSection,
  Faq,
  ForTeams,
  HeroIntro,
  HowItWorks,
  Pricing,
  SiteFooter,
  SiteHeader,
} from "@/components/Site/Landing"

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
  return (
    <ContactProvider>
      <div className="min-h-svh bg-background">
        <SiteHeader />
        <main>
          <Checker intro={<HeroIntro />} />
          <HowItWorks />
          <ForTeams />
          <Pricing />
          <Faq />
          <ContactSection />
        </main>
        <SiteFooter />
      </div>
    </ContactProvider>
  )
}
