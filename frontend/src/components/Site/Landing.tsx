import {
  Archive,
  BadgeCheck,
  Check,
  ClipboardPaste,
  FileCheck2,
  ListChecks,
  type LucideIcon,
  PenLine,
  Plug,
  Users,
} from "lucide-react"
import type { ReactNode } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { track } from "@/lib/analytics"
import { cn } from "@/lib/utils"
import {
  CONTACT_EMAIL,
  ContactForm,
  type Interest,
  useContact,
} from "./Contact"

const NAV = [
  { href: "#how", label: "How it works" },
  { href: "#teams", label: "For teams" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
  { href: "#contact", label: "Contact" },
]

export function Brand() {
  return (
    <a
      href="#check"
      className="flex items-center gap-2 text-lg font-semibold tracking-tight"
    >
      <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <FileCheck2 className="size-4.5" aria-hidden="true" />
      </span>
      <span>
        Check<span className="text-primary">ON</span>
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
    "One click, no sign-up",
    "A compliant rewrite you approve, change by change",
    "Edit, format and copy it straight into your ATS",
  ]
  return (
    <div className="min-w-0 space-y-6">
      <Badge
        variant="outline"
        className="gap-1.5 rounded-full px-3 py-1 text-left text-xs font-medium whitespace-normal"
      >
        <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
        Ontario job posting compliance
      </Badge>
      <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
        Ontario compliance check for your job postings,{" "}
        <span className="text-primary">in one click.</span>
      </h1>
      <p className="max-w-xl text-lg text-muted-foreground">
        Paste a posting and CheckON shows what doesn't comply, then rewrites it
        for you before you publish.
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
      title: "Check it in one click",
      text: "See what complies and what doesn't, pointing at the exact sentence.",
    },
    {
      icon: BadgeCheck,
      title: "Approve the fixes",
      text: "Only what compliance requires changes. You keep or drop each change.",
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

export function ForTeams() {
  const { contactAbout } = useContact()
  return (
    <Section
      id="teams"
      eyebrow="For agencies and HR teams"
      title="Check every posting where you already write it"
      lead="Recruiting agencies post for many clients. HR teams post from their HR system. Tell us how you work and we'll set CheckON up for you."
      muted
    >
      <div className="grid gap-4 md:grid-cols-3">
        <Tile icon={Users} title="A profile per client">
          Settings saved for each client, so every posting is checked against
          the right facts.
        </Tile>
        <Tile icon={Plug} title="Runs in your HR system">
          A browser extension for any job form, and connections to HR systems,
          starting with BambooHR.
        </Tile>
        <Tile icon={Archive} title="Proof for your clients">
          A dated record of every approved posting.
        </Tile>
      </div>
      <Button
        className="mt-6"
        variant="outline"
        onClick={() => contactAbout("custom")}
      >
        Talk to us about your setup
      </Button>
    </Section>
  )
}

interface Plan {
  name: string
  price: string
  period?: string
  note: string
  features: string[]
  cta: { label: string; interest?: Interest }
  highlight?: boolean
}

const PLANS: Plan[] = [
  {
    name: "Free",
    price: "$0",
    note: "Available now",
    features: [
      "1 check a week",
      "No sign-up",
      "Compliant rewrite you approve",
      "Edit and copy the result",
    ],
    cta: { label: "Check a posting" },
    highlight: true,
  },
  {
    name: "Starter",
    price: "$79",
    period: "/month",
    note: "Contact us to get started",
    features: [
      "50 checks a month",
      "Company profile and history",
      "Browser extension",
    ],
    cta: { label: "Contact us", interest: "starter" },
  },
  {
    name: "Agency",
    price: "$249",
    period: "/month",
    note: "Contact us to get started",
    features: [
      "300 checks a month",
      "A workspace per client",
      "Archive of approved postings",
    ],
    cta: { label: "Contact us", interest: "agency" },
  },
  {
    name: "Custom setup",
    price: "Quote",
    note: "Priced for your setup",
    features: [
      "Connect your HR system",
      "Your wording and approvals",
      "Tested on your own postings",
    ],
    cta: { label: "Contact us for a quote", interest: "custom" },
  },
]

export function Pricing() {
  const { contactAbout } = useContact()
  return (
    <Section
      id="pricing"
      eyebrow="Pricing"
      title="Start free. Upgrade when it's part of your workflow."
      lead="Prices in Canadian dollars."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {PLANS.map((plan) => (
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
              {plan.period && (
                <span className="text-sm text-muted-foreground">
                  {plan.period}
                </span>
              )}
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
            {plan.cta.interest ? (
              <Button
                variant="outline"
                className="mt-6"
                onClick={() => {
                  if (!plan.cta.interest) return
                  track("plan-click", { plan: plan.cta.interest })
                  contactAbout(plan.cta.interest)
                }}
              >
                {plan.cta.label}
              </Button>
            ) : (
              <Button asChild className="mt-6">
                <a href="#check">{plan.cta.label}</a>
              </Button>
            )}
          </div>
        ))}
      </div>
    </Section>
  )
}

const QUESTIONS = [
  {
    q: "Is this legal advice?",
    a: "No. CheckON checks your posting against Ontario's job posting requirements and shows where each finding comes from. For advice on your situation, talk to an employment lawyer.",
  },
  {
    q: "Who is it for?",
    a: "Ontario employers and the recruiting agencies that post for them. If the requirements don't apply to a posting, CheckON tells you.",
  },
  {
    q: "Do you keep my posting?",
    a: "No. It's processed by our AI provider to run the check and held for up to an hour while you review the results. We keep it only if you choose to share it when you report a problem.",
  },
  {
    q: "What does the rewrite change?",
    a: "Only what compliance requires. Everything else stays exactly as you wrote it, and you approve each change before it's applied.",
  },
  {
    q: "How do I get more checks or a custom setup?",
    a: "Contact us below. Starter and Agency plans and custom setups are arranged directly with us for now.",
  },
]

export function Faq() {
  return (
    <Section id="faq" eyebrow="FAQ" title="Questions people ask" muted>
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

export function ContactSection() {
  return (
    <Section
      id="contact"
      eyebrow="Contact"
      title="Talk to us"
      lead="Questions, a plan for your team, or a custom setup for your HR system: send us a message and we'll reply by email."
    >
      <div className="max-w-2xl">
        <ContactForm />
      </div>
    </Section>
  )
}

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <Brand />
        <p>Ontario job posting compliance. Not legal advice.</p>
        <p className="flex items-center gap-4">
          {CONTACT_EMAIL ? (
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="hover:text-foreground"
            >
              {CONTACT_EMAIL}
            </a>
          ) : (
            <a href="#contact" className="hover:text-foreground">
              Contact
            </a>
          )}
          <span>© {new Date().getFullYear()} CheckON · checkon.ca</span>
        </p>
      </div>
    </footer>
  )
}
