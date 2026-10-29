import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowRight } from "lucide-react"
import { useEffect } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { GuideLinks } from "@/components/Site/Guide"
import { JsonLd, ORGANIZATION } from "@/components/Site/JsonLd"
import { Brand, SiteFooter } from "@/components/Site/Landing"
import { List, PageLink, Part } from "@/components/Site/Legal"
import { RuleLinks } from "@/components/Site/RulePage"
import { RULES } from "@/components/Site/rules/en"
import { RULES as RULES_FR } from "@/components/Site/rules/fr"
import { Button } from "@/components/ui/button"
import { loadAnalytics, track } from "@/lib/analytics"
import { pageHead, SITE } from "@/lib/seo"

// Plain words only, no section numbers (marketing copy). Every statement matches the rule pack
// (backend/rulepacks/CA-ON/rules.yaml) and docs/law-review-2026-10.md; change this page when they change. Each rule
// has its own page with the sections cited (components/Site/rules), linked from here.
const UPDATED = "2026-10-23"
const MINISTRY_GUIDE =
  "https://www.ontario.ca/document/your-guide-employment-standards-act-0/requirements-related-publicly-advertised-job"
const TITLE =
  "Ontario job posting requirements (2026): what every posting must include"
const DESCRIPTION =
  "Since January 1, 2026, Ontario job postings must show the expected pay, say whether the job is an existing vacancy, disclose AI screening and drop Canadian experience requirements. Here's what each one means, in plain words."

export const Route = createFileRoute("/ontario-job-posting-requirements")({
  component: Requirements,
  head: () =>
    pageHead({
      path: "/ontario-job-posting-requirements",
      title: `${TITLE} | CheckON`,
      description: DESCRIPTION,
    }),
})

const cta = (name: string) => () =>
  track("content-cta", { page: "requirements", cta: name })

function Check({ children }: { children: string }) {
  return (
    <Button asChild size="lg">
      <Link to="/check" hash="check" onClick={cta("check")}>
        {children} <ArrowRight />
      </Link>
    </Button>
  )
}

function Requirements() {
  useEffect(loadAnalytics, [])
  return (
    <div className="site min-h-svh bg-background text-foreground">
      <JsonLd
        data={{
          "@type": "Article",
          headline: TITLE,
          description: DESCRIPTION,
          dateModified: UPDATED,
          mainEntityOfPage: `${SITE}/ontario-job-posting-requirements`,
          author: ORGANIZATION,
          publisher: ORGANIZATION,
        }}
      />
      <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Brand href="/check" />
          <div className="flex items-center gap-2">
            <Appearance />
            <Button asChild size="sm">
              <Link to="/check" hash="check" onClick={cta("header-check")}>
                Check a posting
              </Link>
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-10 px-4 py-16 sm:px-6 sm:py-20">
        <div className="space-y-4">
          <p className="text-sm font-medium text-primary">
            Ontario job postings
          </p>
          <h1 className="font-display text-5xl leading-tight font-medium tracking-[-0.015em] text-balance">
            What an Ontario job posting must include
          </h1>
          <p className="text-lg text-muted-foreground">
            Since January 1, 2026, Ontario employers with 25 or more employees
            must follow job posting rules for every job they advertise to the
            public. Here is what the rules ask for, in plain words, and how to
            check a posting against them.
          </p>
          <p className="text-sm text-muted-foreground">
            Updated October 23, 2026. A summary, not legal advice.
          </p>
        </div>

        <Part title="Who the rules apply to">
          <List>
            <li>
              <strong>Employers with 25 or more employees in Ontario</strong> on
              the day the job is posted. Count people, not full-time
              equivalents: part-time and casual staff and anyone on leave each
              count as one.
            </li>
            <li>
              <strong>Public postings for a specific job</strong> in Ontario,
              wherever they appear: your careers page, a job board or a
              recruiter's site. You're responsible for a posting a recruiter or
              job board publishes for you.
            </li>
            <li>
              <strong>Not covered:</strong> a general "we're hiring" campaign
              with no specific job, a posting open only to your current
              employees, and work done outside Ontario.
            </li>
            <li>
              A document or web page the posting links to counts as part of the
              posting.
            </li>
          </List>
        </Part>

        <Part title="What every posting must include">
          <List>
            <li>
              <strong>The expected pay or a pay range.</strong> A range can be
              at most $50,000 a year wide. Postings where the expected pay is
              above $200,000 a year are exempt.{" "}
              <PageLink to={RULES.pay.path}>More on pay ranges</PageLink>
            </li>
            <li>
              <strong>Whether the job is an existing vacancy.</strong> Say
              plainly whether you're filling a vacancy that exists now or not,
              for example "This posting is for an existing vacancy."{" "}
              <PageLink to={RULES.vacancy.path}>
                More on the vacancy statement
              </PageLink>
            </li>
            <li>
              <strong>
                Whether you use AI to screen, assess or select applicants.
              </strong>{" "}
              If you, or a recruiter working for you, use AI tools to screen,
              assess or select applicants, the posting must say so.{" "}
              <PageLink to={RULES.ai.path}>More on AI disclosure</PageLink>
            </li>
            <li>
              <strong>No Canadian experience requirement</strong>, in the
              posting or its application form. Ask for the skill or the years of
              experience, not where the experience was gained.{" "}
              <PageLink to={RULES.cex.path}>
                More on Canadian experience
              </PageLink>
            </li>
          </List>
        </Part>

        <Part title="After you post">
          <List>
            <li>
              <strong>Tell interviewed applicants where things stand.</strong>{" "}
              Within 45 days of an interview (or the last one), tell each
              applicant you interviewed whether a hiring decision has been made,
              in person, in writing, or by email, text or a portal update.{" "}
              <PageLink to={RULES.interview.path}>
                More on the 45-day rule
              </PageLink>
            </li>
            <li>
              <strong>Keep records for three years.</strong> Keep a copy of each
              posting and any application form for three years after the posting
              comes down, and what you told each interviewed applicant for three
              years.{" "}
              <PageLink to={RULES.records.path}>
                More on record keeping
              </PageLink>
            </li>
          </List>
        </Part>

        <Part title="Each rule in detail">
          <p>
            What the law says, with the sections, wording you can copy and a
            before and after.{" "}
            <PageLink to={RULES_FR.pay.path}>
              <span lang="fr-CA">Aussi en français.</span>
            </PageLink>
          </p>
          <RuleLinks lang="en" />
        </Part>

        <Part title="Checklist, template and guides">
          <p>
            Tools to use when you write or review a posting: a checklist to copy
            or print, a template with the required lines in place, a guide for
            recruiters posting for clients, and how accurate CheckON is.
          </p>
          <GuideLinks />
        </Part>

        <Part title="Check your posting">
          <p>
            CheckON reads a posting and gives each requirement a verdict,
            quoting the sentence it's about. When something is missing, it
            suggests the smallest change that fixes it, and nothing changes
            until you approve it. The first check each week is free, with no
            sign-up.
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Check>Check a posting free</Check>
            <Button asChild size="lg" variant="outline">
              <Link to="/check" hash="audit" onClick={cta("audit")}>
                Audit your careers page
              </Link>
            </Button>
          </div>
        </Part>

        <p className="border-t pt-6 text-sm text-muted-foreground">
          Source: the Government of Ontario's{" "}
          <a
            href={MINISTRY_GUIDE}
            className="text-primary underline-offset-4 hover:underline"
            rel="noreferrer"
            target="_blank"
          >
            guide to the job posting requirements
          </a>
          . This page summarises them and isn't legal advice; for your
          situation, talk to an employment lawyer.
        </p>
      </main>
      <SiteFooter home="/check" />
    </div>
  )
}
