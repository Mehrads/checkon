import "@fontsource-variable/newsreader/wght.css"
import "@fontsource-variable/hanken-grotesk/wght.css"
import "./landing.css"

import { Link } from "@tanstack/react-router"
import { ArrowRight, Check, ExternalLink } from "lucide-react"
import type { ReactNode } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import { track } from "@/lib/analytics"
import { cn } from "@/lib/utils"
import { CONTACT_EMAIL, ContactForm } from "./Contact"
import { GUIDE_IDS, GUIDES } from "./guides"
import { Photo } from "./Media"
import { RULES } from "./rules/en"
import { RULES as RULES_FR } from "./rules/fr"
import { RULE_IDS } from "./rules/types"

// In-page sections, then the pages about how accurate the check is and what the rules ask. `wide`: only from
// 1280px, so the bar fits at 1024 (the sample sits right under the hero, and the hero links to it).
const NAV = [
  { href: "#how", label: "How it works" },
  { href: "#sample", label: "Sample result", wide: true },
  { href: "#audit", label: "Careers page audit" },
  { href: "#open-source", label: "Open source" },
]
const NAV_PAGES = [
  { to: GUIDES.accuracy.path, label: "Accuracy" },
  { to: "/ontario-job-posting-requirements", label: "Guides" },
]
/** The source code, and the browser extension in it (built against your own server: extension/README.md). */
export const REPO_URL = "https://github.com/Mehrads/checkon"
const EXTENSION_URL = `${REPO_URL}/tree/main/extension`

export function Brand({ href = "#check" }: { href?: string }) {
  return (
    <a href={href}>
      <Logo asLink={false} />
    </a>
  )
}

export function SiteHeader() {
  return (
    <header className="glass-bar sticky top-2 z-30 mx-2 mt-2 rounded-full sm:mx-4 md:mx-(--shell-x)">
      <div className="flex h-12 items-center justify-between gap-3 pr-2 pl-3">
        <Brand />
        <nav
          aria-label="Sections"
          className="hidden items-center gap-3.5 whitespace-nowrap text-sm text-muted-foreground lg:flex xl:gap-7"
        >
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={cn(
                "transition-colors hover:text-foreground",
                item.wide && "hidden xl:inline",
              )}
            >
              {item.label}
            </a>
          ))}
          {NAV_PAGES.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="transition-colors hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-1.5">
          {/* Phones follow the system theme, which leaves room for the main button */}
          <div className="hidden sm:block">
            <Appearance className="size-8 rounded-full border-0 bg-solid text-on-solid hover:bg-solid/85 hover:text-on-solid dark:bg-solid dark:hover:bg-solid/85" />
          </div>
          <Button
            asChild
            size="sm"
            variant="ghost"
            className="hidden sm:inline-flex"
          >
            <Link to={isLoggedIn() ? "/" : "/login"}>
              {isLoggedIn() ? "Your account" : "Log in"}
            </Link>
          </Button>
          <Button asChild size="sm">
            <a href="#check">
              <span className="max-[359px]:hidden">Check a posting</span>
              <span className="hidden max-[359px]:inline">Check</span>
            </a>
          </Button>
        </div>
      </div>
    </header>
  )
}

/** A short rule and a label above a heading. */
export function Kicker({
  children,
  className,
  rule = "bg-brand",
}: {
  children: ReactNode
  className?: string
  rule?: string
}) {
  return (
    <p
      className={cn(
        "flex items-center gap-3 text-sm font-medium text-muted-foreground",
        className,
      )}
    >
      <span className={cn("h-px w-8", rule)} aria-hidden="true" />
      {children}
    </p>
  )
}

export function Heading({
  id,
  children,
  className,
}: {
  id?: string
  children: ReactNode
  className?: string
}) {
  return (
    <h2
      id={id}
      className={cn(
        "font-display text-[2.125rem] leading-[1.08] font-medium tracking-[-0.015em] text-balance sm:text-5xl",
        className,
      )}
    >
      {children}
    </h2>
  )
}

export function HeroIntro() {
  const facts = [
    ["Quotes the line", "Each verdict points at your words"],
    ["Shows the source", "Linked to the official text"],
    ["Yours to approve", "Change by change"],
  ]
  const link =
    "inline-flex items-center gap-1.5 font-medium text-deep-foreground underline decoration-deep-accent underline-offset-4 hover:decoration-2"
  return (
    <div className="min-w-0 text-deep-foreground">
      <Kicker className="text-deep-muted max-sm:hidden" rule="bg-deep-accent">
        For recruiters, agencies and HR teams in Ontario
      </Kicker>
      <h1 className="font-display text-[2.3rem] leading-[1.04] font-medium tracking-[-0.02em] text-balance sm:mt-6 sm:text-6xl sm:leading-[1.02]">
        Check a job posting{" "}
        <span className="text-deep-accent">line by line</span> before it goes
        live.
      </h1>
      <p className="mt-4 max-w-xl text-deep-muted sm:mt-6 sm:text-lg">
        Paste a posting or its link. CheckON quotes each line that doesn't meet
        Ontario's job posting rules, with its source and the smallest fix. You
        approve every change.
      </p>
      <p className="mt-4 text-sm sm:mt-6">
        <Link
          to={GUIDES.accuracy.path}
          onClick={() => track("hero-accuracy")}
          className={link}
        >
          Tested on 150 real Ontario postings
          <ArrowRight className="size-4 shrink-0" aria-hidden="true" />
        </Link>
      </p>
      {/* Chrome on a phone can't run extensions, and the hero has no room to spare there */}
      <p className="mt-2 text-sm max-sm:hidden">
        <a
          href={EXTENSION_URL}
          target="_blank"
          rel="noreferrer"
          onClick={() => track("hero-extension")}
          className={link}
        >
          Check in your ATS or job board with the Chrome extension
          <ExternalLink className="size-4 shrink-0" aria-hidden="true" />
        </a>
      </p>
      <dl className="mt-10 hidden max-w-xl gap-x-6 gap-y-4 border-t border-white/15 pt-5 text-sm sm:grid sm:grid-cols-3">
        {facts.map(([term, detail]) => (
          <div key={term}>
            <dt className="font-semibold">{term}</dt>
            <dd className="mt-0.5 text-deep-muted">{detail}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

/** The hero's way in for a visitor without a posting at hand: the sample result further down the page. */
export function SampleHint() {
  return (
    <Link
      to="/check"
      hash="sample"
      onClick={() => track("hero-sample")}
      className="font-medium text-primary underline-offset-4 hover:underline"
    >
      No posting at hand? See a real result on a sample posting
    </Link>
  )
}

/** For agencies: what an account adds when you post for many clients. */
export function ForAgencies() {
  const points = [
    "A workspace per client, each with its own company profile, so a check starts from that client's answers",
    "Audit a client's careers page, then fix each posting with a check",
    "An archive of every posting you approved",
  ]
  return (
    <section aria-labelledby="agencies">
      <div className="mx-auto max-w-6xl px-4 pb-20 sm:px-6 sm:pb-28">
        <div className="relative isolate overflow-hidden rounded-xl bg-deep p-6 text-deep-foreground [--ink:var(--deep-accent)] [--on-ink:var(--deep)] sm:p-10 lg:grid lg:grid-cols-12 lg:gap-8">
          <div className="lg:col-span-5">
            <Kicker className="text-deep-muted" rule="bg-deep-accent">
              For agencies
            </Kicker>
            <h2
              id="agencies"
              className="mt-5 font-display text-[2rem] leading-[1.08] font-medium tracking-[-0.015em] text-balance sm:text-4xl"
            >
              Posting for many clients?
            </h2>
            <p className="mt-5 text-deep-muted">
              Every client's postings, checked the same way, with a record of
              what you checked and approved.
            </p>
          </div>
          <div className="mt-8 lg:col-span-6 lg:col-start-7 lg:mt-1">
            <ul className="space-y-3">
              {points.map((point) => (
                <li key={point} className="flex gap-3">
                  <Check
                    className="mt-1 size-4 shrink-0 text-deep-accent"
                    aria-hidden="true"
                  />
                  {point}
                </li>
              ))}
            </ul>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link
                  to="/check"
                  hash="check"
                  onClick={() => track("agency-check")}
                >
                  Check a posting
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="border-white/30 bg-transparent text-deep-foreground hover:bg-white/10 hover:text-deep-foreground"
              >
                <Link
                  to={GUIDES.recruiters.path}
                  onClick={() => track("agency-guide")}
                >
                  Read the guide for recruiters
                </Link>
              </Button>
            </div>
          </div>
          <Photo
            name="bg-pen"
            widths={[960, 1600]}
            width={1600}
            height={1201}
            sizes="(min-width: 1024px) 1100px, 100vw"
            alt=""
            className="absolute inset-0 -z-20 h-full w-full object-cover object-[65%_center]"
          />
          <div
            className="absolute inset-0 -z-10 bg-deep/90"
            aria-hidden="true"
          />
        </div>
      </div>
    </section>
  )
}

export function HowItWorks() {
  const steps = [
    {
      title: "Paste one posting",
      text: "From your ATS, a job board draft or a Word file. Up to 8,000 characters, nothing to install.",
    },
    {
      title: "Check it",
      text: "Each requirement gets a verdict, pointing at the exact sentence. If the answer depends on something only you know, CheckON asks a yes-or-no question.",
    },
    {
      title: "Approve the fixes",
      text: "Only what compliance requires is changed. Keep or drop each change.",
    },
    {
      title: "Edit and copy",
      text: "Tidy the wording and formatting, then copy it back where you publish, formatted or as plain text.",
    },
  ]
  return (
    <section id="how" className="scroll-mt-16">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-12 lg:gap-8">
        <div className="lg:col-span-5">
          <Kicker>How it works</Kicker>
          <Heading className="mt-5">
            From a pasted draft to a posting you can publish
          </Heading>
        </div>
        <ol className="space-y-3 lg:col-span-6 lg:col-start-7 lg:mt-2">
          {steps.map((step, index) => (
            <li
              key={step.title}
              className="grid grid-cols-[2.5rem_1fr] gap-3 rounded-xl border bg-card p-5 shadow-sm"
            >
              <span
                className="flex size-8 items-center justify-center rounded-full bg-solid text-sm font-semibold text-on-solid shadow-sm"
                aria-hidden="true"
              >
                {index + 1}
              </span>
              <div>
                <h3 className="font-semibold">{step.title}</h3>
                <p className="mt-1.5 text-muted-foreground">{step.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

const OPEN_SOURCE = [
  "Free to use, under the Apache-2.0 licence",
  "Run it on your own server, and build the Chrome extension against it",
  "The rules, prompts and rule data are in the code, to read and change",
]

/** CheckON is free and open source: anyone can run their own copy. */
export function OpenSource() {
  return (
    <section id="open-source" className="scroll-mt-16">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-12 lg:gap-8">
        <div className="lg:col-span-5">
          <Kicker>Open source</Kicker>
          <Heading className="mt-5">Free, and yours to run</Heading>
          <p className="mt-5 text-muted-foreground">
            CheckON's code is public. Use this site, or host CheckON yourself
            for your team.
          </p>
        </div>
        <div className="lg:col-span-6 lg:col-start-7 lg:mt-2">
          <ul className="space-y-3">
            {OPEN_SOURCE.map((point) => (
              <li
                key={point}
                className="flex gap-3 rounded-xl border bg-card p-5 shadow-sm"
              >
                <Check
                  className="mt-1 size-4 shrink-0 text-primary"
                  aria-hidden="true"
                />
                {point}
              </li>
            ))}
          </ul>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <a
                href={REPO_URL}
                target="_blank"
                rel="noreferrer"
                onClick={() => track("open-source")}
              >
                See the code on GitHub <ExternalLink />
              </a>
            </Button>
            <Button asChild size="lg" variant="outline">
              <a href="#check">Check a posting</a>
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}

export const QUESTIONS = [
  {
    q: "Is this legal advice?",
    a: "No. CheckON checks your posting against Ontario's job posting requirements and shows where each finding comes from. For advice on your situation, talk to an employment lawyer.",
  },
  {
    q: "Who is it for?",
    a: "Recruiters and staffing agencies that post for Ontario clients, and the HR teams of Ontario employers. If the requirements don't apply to a posting, CheckON tells you.",
  },
  {
    q: "How accurate is it?",
    a: "We ran it on 150 real Ontario job postings in October 2026 and compared each verdict with a separate reading of the law. Depending on the rule, they agreed 95% to 99% of the time. Our accuracy page has the method, the numbers and what it still gets wrong.",
  },
  {
    q: "Do you keep my posting?",
    a: "No. It's sent to the AI provider to run the check and held for up to an hour while you review the results. It's kept only if you share it when you report a problem, or turn on the archive for a company profile. Otherwise an account keeps only the date, job title and result of each check.",
  },
  {
    q: "What does the rewrite change?",
    a: "Only what compliance requires. Everything else stays exactly as you wrote it, and you approve each change before it's applied.",
  },
  {
    q: "What doesn't it check?",
    a: "It checks the posting you paste or link to, and its application form when you add the form's questions (that uses one more check). A document the posting links to, and anything that happens after you post, are outside the check.",
  },
  {
    q: "Does it cost anything?",
    a: "No. CheckON is free and open source under the Apache-2.0 licence. Without an account you get the free check; an account adds a company profile, client workspaces, careers page audits and the archive. You can also run CheckON on your own server.",
  },
]

export function Faq() {
  return (
    <section id="faq" className="scroll-mt-16">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-12 lg:gap-8">
        <div className="lg:col-span-4">
          <Kicker>FAQ</Kicker>
          <Heading className="mt-5">Questions people ask</Heading>
          <p className="mt-5 text-muted-foreground">
            Something else?{" "}
            <a
              href="#contact"
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              Send us a message
            </a>
            .
          </p>
        </div>
        <div className="space-y-2 lg:col-span-7 lg:col-start-6">
          {QUESTIONS.map((item) => (
            <details
              key={item.q}
              className="group rounded-xl border bg-card px-5 py-4 shadow-sm"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
                {item.q}
                <span
                  className="text-xl text-primary transition-transform group-open:rotate-45"
                  aria-hidden="true"
                >
                  +
                </span>
              </summary>
              <p className="mt-3 max-w-prose text-muted-foreground">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}

export function ContactSection() {
  return (
    <section id="contact" className="scroll-mt-16">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-12 lg:gap-8">
        <div className="lg:col-span-4">
          <Kicker>Contact</Kicker>
          <Heading className="mt-5">Get in touch</Heading>
          <p className="mt-5 text-muted-foreground">
            Questions about CheckON, or a setup for your team. The message goes
            to whoever runs this site, and the reply comes by email.
          </p>
        </div>
        <div className="lg:col-span-7 lg:col-start-6">
          <ContactForm />
        </div>
      </div>
    </section>
  )
}

/** `home` prefixes the in-page anchors, for pages other than the checker; `note` is the line under the logo. */
export function SiteFooter({
  home = "",
  note = "Ontario job posting compliance. Not legal advice.",
}: {
  home?: string
  note?: string
}) {
  return (
    <footer className="border-t">
      <div className="mx-auto max-w-6xl space-y-8 px-4 py-10 text-sm text-muted-foreground sm:px-6">
        <nav aria-labelledby="footer-guides">
          <h2 id="footer-guides" className="font-medium text-foreground">
            Guides and templates
          </h2>
          <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
            {GUIDE_IDS.map((id) => (
              <li key={id}>
                <Link to={GUIDES[id].path} className="hover:text-foreground">
                  {GUIDES[id].name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <nav aria-labelledby="footer-rules">
          <h2 id="footer-rules" className="font-medium text-foreground">
            Ontario's rules
          </h2>
          <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
            <li>
              <Link
                to="/ontario-job-posting-requirements"
                className="hover:text-foreground"
              >
                Ontario job posting requirements
              </Link>
            </li>
            {RULE_IDS.map((id) => (
              <li key={id}>
                <Link to={RULES[id].path} className="hover:text-foreground">
                  {RULES[id].name}
                </Link>
              </li>
            ))}
            <li>
              <Link
                to={RULES_FR.pay.path}
                hrefLang="fr-CA"
                lang="fr-CA"
                className="hover:text-foreground"
              >
                Lisez-les en français
              </Link>
            </li>
          </ul>
        </nav>
        <div className="flex flex-col gap-6 border-t pt-8 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-3">
            <Brand href={`${home}#check`} />
            <p>{note}</p>
          </div>
          <p className="flex flex-wrap items-center gap-x-5 gap-y-2">
            {CONTACT_EMAIL ? (
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="hover:text-foreground"
              >
                {CONTACT_EMAIL}
              </a>
            ) : (
              <a href={`${home}#contact`} className="hover:text-foreground">
                Contact
              </a>
            )}
            <Link to="/privacy" className="hover:text-foreground">
              Privacy
            </Link>
            <Link to="/terms" className="hover:text-foreground">
              Terms
            </Link>
            <Link
              to={isLoggedIn() ? "/" : "/login"}
              className="hover:text-foreground"
            >
              {isLoggedIn() ? "Your account" : "Log in"}
            </Link>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
              className="hover:text-foreground"
            >
              CheckON · open source, Apache-2.0
            </a>
          </p>
        </div>
      </div>
    </footer>
  )
}
