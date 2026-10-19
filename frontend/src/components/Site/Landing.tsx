import {
  Archive,
  BadgeCheck,
  Bot,
  Building2,
  CalendarClock,
  Check,
  ClipboardPaste,
  DollarSign,
  FileCheck2,
  Globe2,
  ListChecks,
  type LucideIcon,
  PenLine,
  Plug,
  Users,
} from "lucide-react"
import type { ReactNode } from "react"
import { RequestForm } from "@/components/Check/Research"
import { Appearance } from "@/components/Common/Appearance"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const NAV = [
  { href: "#how", label: "How it works" },
  { href: "#rules", label: "What we check" },
  { href: "#teams", label: "For teams" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
]

export function Brand() {
  return (
    <a
      href="#check"
      className="flex items-center gap-2 font-semibold tracking-tight"
    >
      <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <FileCheck2 className="size-4.5" aria-hidden="true" />
      </span>
      <span>
        Posting<span className="text-primary">Check</span>
        <span className="ml-1.5 hidden text-xs font-normal text-muted-foreground sm:inline">
          Ontario
        </span>
      </span>
    </a>
  )
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Brand />
        <nav
          aria-label="Sections"
          className="hidden items-center gap-6 whitespace-nowrap text-sm text-muted-foreground lg:flex"
        >
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="transition-colors hover:text-foreground"
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Appearance />
          <Button asChild size="sm">
            <a href="#check">Check a posting</a>
          </Button>
        </div>
      </div>
    </header>
  )
}

export function HeroIntro() {
  const points = [
    "Pay range, vacancy statement and AI disclosure, checked line by line",
    "Canadian-experience wording rewritten to ask for the skill instead",
    "A rewrite you approve, then edit and copy into your ATS",
  ]
  return (
    <div className="min-w-0 space-y-6">
      <Badge
        variant="outline"
        className="gap-1.5 rounded-full px-3 py-1 text-left text-xs font-medium whitespace-normal"
      >
        <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
        Ontario's job posting rules, in force since January 1, 2026
      </Badge>
      <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
        Job postings that follow the rules,{" "}
        <span className="text-primary">and get more applicants.</span>
      </h1>
      <p className="max-w-xl text-lg text-muted-foreground">
        64% of Canadian job seekers have skipped a posting with no salary. Paste
        yours: we check it against Ontario's rules and rewrite what's missing,
        before you publish.
      </p>
      <ul className="space-y-2.5">
        {points.map((point) => (
          <li key={point} className="flex items-start gap-2.5 text-sm">
            <Check
              className="mt-0.5 size-4 shrink-0 text-primary"
              aria-hidden="true"
            />
            {point}
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        Job seeker figure: Employment Hero survey, January 2026.
      </p>
    </div>
  )
}

function Section({
  id,
  eyebrow,
  title,
  lead,
  children,
  muted = false,
}: {
  id: string
  eyebrow: string
  title: string
  lead?: string
  children: ReactNode
  muted?: boolean
}) {
  return (
    <section
      id={id}
      className={cn("scroll-mt-16 border-t", muted && "bg-muted/30")}
    >
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
        <div className="max-w-2xl space-y-3">
          <p className="text-sm font-medium text-primary">{eyebrow}</p>
          <h2 className="text-3xl font-semibold tracking-tight text-balance">
            {title}
          </h2>
          {lead && <p className="text-muted-foreground">{lead}</p>}
        </div>
        <div className="mt-10">{children}</div>
      </div>
    </section>
  )
}

function Tile({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon
  title: string
  children: ReactNode
}) {
  return (
    <div className="rounded-xl border bg-card p-5 shadow-sm">
      <Icon className="size-5 text-primary" aria-hidden="true" />
      <h3 className="mt-3 font-semibold">{title}</h3>
      <p className="mt-1.5 text-sm text-muted-foreground">{children}</p>
    </div>
  )
}

export function HowItWorks() {
  const steps = [
    {
      icon: ClipboardPaste,
      title: "Paste your posting",
      text: "From your ATS, a job board draft or your careers page. Nothing to install.",
    },
    {
      icon: ListChecks,
      title: "See every rule checked",
      text: "Each verdict points at the sentence it's about, with the rule it comes from.",
    },
    {
      icon: BadgeCheck,
      title: "Approve the fixes",
      text: "Only what the rules require changes. You keep or drop each change.",
    },
    {
      icon: PenLine,
      title: "Edit and copy",
      text: "Polish the wording and formatting, then copy it back where you publish.",
    },
  ]
  return (
    <Section
      id="how"
      eyebrow="How it works"
      title="From draft to compliant in about a minute"
    >
      <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step, index) => (
          <li
            key={step.title}
            className="rounded-xl border bg-card p-5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <step.icon className="size-5 text-primary" aria-hidden="true" />
              <span className="text-sm font-medium text-muted-foreground">
                0{index + 1}
              </span>
            </div>
            <h3 className="mt-3 font-semibold">{step.title}</h3>
            <p className="mt-1.5 text-sm text-muted-foreground">{step.text}</p>
          </li>
        ))}
      </ol>
    </Section>
  )
}

export function WhatWeCheck() {
  return (
    <Section
      id="rules"
      eyebrow="What we check"
      title="Every rule a public posting has to meet"
      lead="The rules apply to employers with 25 or more employees in Ontario, for publicly advertised jobs in Ontario. We look up the employer named in your posting; if we can't find it, we assume the rules apply."
      muted
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile icon={DollarSign} title="Expected pay">
          A salary or pay range, no more than $50,000 a year wide, unless the
          pay is above $200,000.
        </Tile>
        <Tile icon={Building2} title="Vacancy statement">
          Whether the posting is for an existing vacancy. We add the statement
          once you tell us.
        </Tile>
        <Tile icon={Bot} title="AI disclosure">
          A statement when AI helps screen, assess or select applicants,
          including ATS ranking.
        </Tile>
        <Tile icon={Globe2} title="No Canadian experience">
          No requirement for Canadian experience. We keep the skill and drop
          where it was gained.
        </Tile>
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="flex gap-4 rounded-xl border border-dashed p-5">
          <CalendarClock
            className="size-5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">
              45-day follow-up.
            </span>{" "}
            Reminders to tell interviewed applicants about your decision. Coming
            with HR-system connections.
          </p>
        </div>
        <div className="flex gap-4 rounded-xl border border-dashed p-5">
          <Archive
            className="size-5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">3-year records.</span>{" "}
            A dated archive of every approved posting. Coming with accounts.
          </p>
        </div>
      </div>
    </Section>
  )
}

export function ForTeams() {
  return (
    <Section
      id="teams"
      eyebrow="For agencies and HR teams"
      title="Check every posting where you already write it"
      lead="Recruiting agencies post for many clients with different rules and screening tools. HR teams post from their HR system. We're building for both; tell us your setup and we'll start with yours."
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr] lg:items-start">
        <div className="grid gap-4">
          <Tile icon={Users} title="A profile per client">
            Headcount, AI tools and preferred wording saved per client, so each
            posting is checked against the right facts.
          </Tile>
          <Tile icon={Plug} title="Runs in your HR system">
            A browser extension for any job form, and connections to HR systems,
            starting with BambooHR.
          </Tile>
          <Tile icon={Archive} title="Proof for your clients">
            A dated record of every approved posting and the rules it met.
          </Tile>
        </div>
        <div id="setup" className="scroll-mt-20">
          <RequestForm startOpen />
        </div>
      </div>
    </Section>
  )
}

export function Pricing() {
  const plans = [
    {
      name: "Free check",
      price: "$0",
      period: "",
      note: "Available now",
      features: [
        "1 check a week, no sign-up",
        "Verdict for every rule",
        "Rewrite you approve",
        "Edit and copy the result",
      ],
      cta: { label: "Check a posting", href: "#check" },
      highlight: true,
    },
    {
      name: "Starter",
      price: "$79",
      period: "/month",
      note: "Coming soon",
      features: [
        "50 checks a month",
        "Company profile and history",
        "Pay range suggestions with sources",
        "Browser extension",
      ],
      cta: { label: "Get early access", href: "#setup" },
    },
    {
      name: "Agency",
      price: "$249",
      period: "/month",
      note: "Coming soon",
      features: [
        "300 checks a month",
        "A workspace per client",
        "3-year archive",
        "Everything in Starter",
      ],
      cta: { label: "Get early access", href: "#setup" },
    },
    {
      name: "Custom setup",
      price: "From $1,000",
      period: "",
      note: "One-time, plus a plan",
      features: [
        "Connect your HR system",
        "Your wording and approvals",
        "Tested on 10 of your postings",
      ],
      cta: { label: "Tell us your setup", href: "#setup" },
    },
  ]
  return (
    <Section
      id="pricing"
      eyebrow="Pricing"
      title="Start free. Pay when it's part of your workflow."
      lead="Prices in Canadian dollars."
      muted
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={cn(
              "flex flex-col rounded-xl border bg-card p-5 shadow-sm",
              plan.highlight && "border-primary ring-1 ring-primary",
            )}
          >
            <p className="text-sm font-medium">{plan.name}</p>
            <p className="mt-3">
              <span className="text-3xl font-semibold tracking-tight">
                {plan.price}
              </span>
              <span className="text-sm text-muted-foreground">
                {plan.period}
              </span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{plan.note}</p>
            <ul className="mt-5 flex-1 space-y-2 text-sm">
              {plan.features.map((feature) => (
                <li key={feature} className="flex gap-2">
                  <Check
                    className="mt-0.5 size-4 shrink-0 text-primary"
                    aria-hidden="true"
                  />
                  {feature}
                </li>
              ))}
            </ul>
            <Button
              asChild
              variant={plan.highlight ? "default" : "outline"}
              className="mt-6"
            >
              <a href={plan.cta.href}>{plan.cta.label}</a>
            </Button>
          </div>
        ))}
      </div>
    </Section>
  )
}

const QUESTIONS = [
  {
    q: "Is this legal advice?",
    a: "No. It applies Ontario's job posting rules from the Employment Standards Act, 2000 and O. Reg. 476/24, and each result names the rule it used. For advice on your situation, talk to an employment lawyer.",
  },
  {
    q: "Who has to follow these rules?",
    a: "Employers with 25 or more employees in Ontario, for public postings that advertise a specific job in Ontario, posted on or after January 1, 2026. Internal postings and general “we're hiring” campaigns are exempt.",
  },
  {
    q: "How do you know how many employees we have?",
    a: "We search the web for the employer named in your posting. If we find it has fewer than 25 employees, the rules don't apply. If we can't find it, we assume they do.",
  },
  {
    q: "Do you keep my posting?",
    a: "No. It's processed by our AI provider to run the check and held for up to an hour while you review the results. We keep it only if you choose to share it when you report a problem.",
  },
  {
    q: "What does the rewrite change?",
    a: "Only what the rules require: it adds missing statements, offers narrower pay ranges for you to choose from, and rewrites Canadian-experience requirements. Everything else stays exactly as you wrote it, and you approve each change.",
  },
  {
    q: "Why one free check a week?",
    a: "Each check runs on AI models we pay for. Plans for teams and agencies are coming; tell us what you need and we'll set you up early.",
  },
]

export function Faq() {
  return (
    <Section id="faq" eyebrow="FAQ" title="Questions people ask">
      <div className="divide-y rounded-xl border bg-card shadow-sm">
        {QUESTIONS.map((item) => (
          <details key={item.q} className="group px-5 py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
              {item.q}
              <span
                className="text-muted-foreground transition-transform group-open:rotate-45"
                aria-hidden="true"
              >
                +
              </span>
            </summary>
            <p className="mt-2 text-sm text-muted-foreground">{item.a}</p>
          </details>
        ))}
      </div>
    </Section>
  )
}

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <Brand />
        <p>
          Not legal advice. Covers Ontario's job posting rules in force since
          January 1, 2026.
        </p>
        <p>© {new Date().getFullYear()}</p>
      </div>
    </footer>
  )
}
