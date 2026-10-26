import "@fontsource-variable/newsreader/wght.css"
import "@fontsource-variable/hanken-grotesk/wght.css"
import "./landing.css"

import { Link } from "@tanstack/react-router"
import { Check } from "lucide-react"
import type { ReactNode } from "react"

import { FREE_ACCOUNT_CHECKS } from "@/components/Billing/UsageMeter"
import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { isLoggedIn } from "@/hooks/useAuth"
import { apiStatus, type PlanId, useCheckout } from "@/hooks/useBilling"
import useCustomToast from "@/hooks/useCustomToast"
import { track } from "@/lib/analytics"
import { cn } from "@/lib/utils"
import {
  CONTACT_EMAIL,
  ContactForm,
  type Interest,
  useContact,
} from "./Contact"
import { Photo } from "./Media"
import { RULES } from "./rules/en"
import { RULES as RULES_FR } from "./rules/fr"
import { RULE_IDS } from "./rules/types"

const NAV = [
  { href: "#how", label: "How it works" },
  { href: "#audit", label: "Careers page audit" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
  { href: "#contact", label: "Contact" },
]

export function Brand({ href = "#check" }: { href?: string }) {
  return (
    <a href={href}>
      <Logo asLink={false} />
    </a>
  )
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b bg-background">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Brand />
        <nav
          aria-label="Sections"
          className="hidden items-center gap-7 whitespace-nowrap text-sm text-muted-foreground lg:flex"
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
            <a href="#check">Check a posting</a>
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
    ["Free", "Once a week, no sign-up"],
    ["Yours to approve", "Change by change"],
    ["Ready to publish", "Copy it into your ATS"],
  ]
  return (
    <div className="min-w-0 text-deep-foreground">
      <Kicker className="text-deep-muted" rule="bg-deep-accent">
        For HR teams and recruiters in Ontario
      </Kicker>
      <h1 className="mt-6 font-display text-[2.6rem] leading-[1.02] font-medium tracking-[-0.02em] text-balance sm:text-6xl">
        Ontario job posting compliance,{" "}
        <span className="text-deep-accent">in one click.</span>
      </h1>
      <p className="mt-6 max-w-xl text-lg text-deep-muted">
        Paste a posting. CheckON marks what doesn't comply, suggests the
        smallest fix for each problem, and leaves every change up to you.
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

/** What a check gives you, shown on one sentence from the sample posting, before and after. */
export function SampleFix() {
  return (
    <section aria-labelledby="sample-fix" className="bg-paper">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-12 lg:gap-8">
        <div className="max-w-xl lg:col-span-5 lg:pt-2">
          <Heading id="sample-fix">
            Every problem, tied to the sentence behind it
          </Heading>
          <p className="mt-6 text-muted-foreground">
            CheckON reads the whole posting and gives each requirement a plain
            verdict. When something needs fixing, it quotes your words and
            suggests the smallest change that fixes it.
          </p>
          <p className="mt-4 text-muted-foreground">
            Nothing is rewritten until you tick it. Your tone, your structure
            and your list of perks stay as you wrote them.
          </p>
        </div>
        <figure className="relative isolate overflow-hidden rounded-xl bg-deep p-6 text-deep-foreground sm:p-10 lg:col-span-7 lg:col-start-6 lg:self-start">
          <figcaption className="text-sm font-medium text-deep-muted">
            One line from a sample posting, checked
          </figcaption>
          <dl className="mt-8 grid gap-x-8 gap-y-3 font-display text-[1.65rem] leading-snug sm:grid-cols-[5rem_1fr] sm:text-3xl">
            <dt className="font-site text-sm font-medium tracking-wide text-deep-muted uppercase sm:pt-2">
              Before
            </dt>
            <dd>
              <del className="decoration-[#e4836a] decoration-2">
                3+ years supervising in a warehouse, with Canadian experience
                required
              </del>
            </dd>
            <dt className="mt-6 font-site text-sm font-medium tracking-wide text-deep-muted uppercase sm:mt-0 sm:pt-2">
              After
            </dt>
            <dd>
              <ins className="no-underline">
                3+ years supervising in a warehouse required
              </ins>
            </dd>
          </dl>
          <p className="mt-8 border-t border-white/15 pt-6 text-deep-muted sm:ml-[7rem]">
            CheckON's note: ask for the skill, not where it was gained.
          </p>
          <Photo
            name="bg-pen"
            widths={[960, 1600]}
            width={1600}
            height={1201}
            sizes="(min-width: 1024px) 660px, 100vw"
            alt="A fountain pen writing on lined paper"
            className="absolute inset-0 -z-20 h-full w-full object-cover object-[65%_center]"
          />
          <div
            className="absolute inset-0 -z-10 bg-deep/85"
            aria-hidden="true"
          />
        </figure>
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
        <ol className="border-t lg:col-span-6 lg:col-start-7 lg:mt-2">
          {steps.map((step, index) => (
            <li
              key={step.title}
              className="grid grid-cols-[2.5rem_1fr] gap-3 border-b py-6"
            >
              <span
                className="font-display text-3xl leading-none text-brand"
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

interface Plan {
  name: string
  price: string
  period?: string
  note: string
  features: string[]
  cta: { label: string; interest?: Interest; checkout?: PlanId; signup?: true }
  highlight?: boolean
}

const PLANS: Plan[] = [
  {
    name: "Free",
    price: "$0",
    note: "No card. Or check once a week without signing up.",
    features: [
      `${FREE_ACCOUNT_CHECKS} checks a month`,
      "History of your checks",
      "Compliant rewrite you approve",
      "Edit and copy the result",
    ],
    cta: { label: "Create a free account", signup: true },
    highlight: true,
  },
  {
    name: "Starter",
    price: "$79",
    period: "/month",
    note: "Billed monthly, cancel anytime. Extra checks $1 each.",
    features: [
      "50 checks a month",
      "History of your checks",
      "Company profile",
      "Pay range suggestions",
      "Archive of approved postings",
    ],
    cta: { label: "Subscribe", interest: "starter", checkout: "starter" },
  },
  {
    name: "Agency",
    price: "$249",
    period: "/month",
    note: "Billed monthly, cancel anytime. Extra checks $1 each.",
    features: [
      "300 checks a month",
      "A workspace per client",
      "Archive of approved postings",
    ],
    cta: { label: "Subscribe", interest: "agency", checkout: "agency" },
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

function PricingSection({ children }: { children: ReactNode }) {
  return (
    <section id="pricing" className="scroll-mt-16">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-28">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Kicker>Pricing</Kicker>
            <Heading className="mt-5 max-w-2xl">
              Start free. Pay when it's part of the job.
            </Heading>
          </div>
          <p className="text-sm text-muted-foreground">
            Prices in Canadian dollars, plus tax where it applies.
          </p>
        </div>
        {children}
      </div>
    </section>
  )
}

export function Pricing() {
  const { contactAbout } = useContact()
  const { showErrorToast } = useCustomToast()
  // Until Stripe is set up (503), or if the payment page can't open, the plan buttons fall back to the contact form.
  const checkout = useCheckout((plan, error) => {
    const status = apiStatus(error)
    if (status === 409) {
      window.location.assign("/")
      return
    }
    if (status !== 503)
      showErrorToast(
        "We couldn't open the payment page. Send us a message instead.",
      )
    contactAbout(plan)
  })
  return (
    <PricingSection>
      <div className="mt-12 grid gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-2 lg:grid-cols-4">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={cn(
              "relative flex flex-col bg-card p-6",
              plan.highlight && "bg-accent",
            )}
          >
            {plan.highlight && (
              <span
                className="absolute inset-x-0 top-0 h-1 bg-brand"
                aria-hidden="true"
              />
            )}
            <h3 className="text-sm font-semibold">{plan.name}</h3>
            <p className="mt-4">
              <span className="font-display text-5xl font-medium tracking-tight">
                {plan.price}
              </span>
              {plan.period && (
                <span className="text-sm text-muted-foreground">
                  {plan.period}
                </span>
              )}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{plan.note}</p>
            <ul className="mt-6 flex-1 space-y-2 border-t pt-5 text-sm">
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
              <LoadingButton
                variant="outline"
                className="mt-6"
                loading={
                  checkout.isPending && checkout.variables === plan.cta.checkout
                }
                disabled={checkout.isPending}
                onClick={() => {
                  if (!plan.cta.interest) return
                  track("plan-click", { plan: plan.cta.interest })
                  if (plan.cta.checkout) checkout.mutate(plan.cta.checkout)
                  else contactAbout(plan.cta.interest)
                }}
              >
                {plan.cta.label}
              </LoadingButton>
            ) : (
              <Button asChild className="mt-6">
                {plan.cta.signup && !isLoggedIn() ? (
                  <Link to="/signup">{plan.cta.label}</Link>
                ) : (
                  <a href="#check">Check a posting</a>
                )}
              </Button>
            )}
          </div>
        ))}
      </div>
    </PricingSection>
  )
}

export const QUESTIONS = [
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
    a: "No. It's processed by our AI provider to run the check and held for up to an hour while you review the results. We keep it only if you share it when you report a problem, or turn on the archive on a paid plan. Otherwise a plan keeps only the date, job title and result of each check.",
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
    q: "How do I get more checks or a custom setup?",
    a: "Create a free account for 5 checks a month, no card needed. For more, pick Starter or Agency above, or contact us below for a custom setup. Plans are billed monthly and you can cancel anytime.",
  },
]

export function Faq() {
  return (
    <section id="faq" className="scroll-mt-16 bg-paper">
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
        <div className="border-t lg:col-span-7 lg:col-start-6">
          {QUESTIONS.map((item) => (
            <details key={item.q} className="group border-b py-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-lg font-medium">
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
          <Heading className="mt-5">Talk to us</Heading>
          <p className="mt-5 text-muted-foreground">
            Questions, a plan for your team, or a custom setup for your HR
            system. Send a message and we'll reply by email.
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
            <span>© {new Date().getFullYear()} CheckON · checkon.ca</span>
          </p>
        </div>
      </div>
    </footer>
  )
}
