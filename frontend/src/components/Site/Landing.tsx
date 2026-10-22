import "@fontsource-variable/newsreader/wght.css"
import "@fontsource-variable/hanken-grotesk/wght.css"
import "./landing.css"

import { Link } from "@tanstack/react-router"
import { Check, Clock } from "lucide-react"
import type { ReactNode } from "react"

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
import { BrowserFrame, Photo, Screenshot } from "./Media"

const NAV = [
  { href: "#how", label: "How it works" },
  { href: "#teams", label: "Who it's for" },
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
function Kicker({
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

function Heading({
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

/** Intrinsic heights of the product captures (all 1120 px wide). */
const PRODUCT = { fixes: 983, findings: 1488, editor: 604 }

/** A red pen on a notebook, with the suggested fixes overlapping it. */
export function WhatYouGet() {
  return (
    <section aria-labelledby="what-you-get" className="overflow-hidden">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 pt-8 pb-20 sm:px-6 lg:grid-cols-12 lg:gap-8 lg:pt-16 lg:pb-32">
        <div className="max-w-xl lg:col-span-5 lg:pt-6 lg:pr-16">
          <Heading id="what-you-get">
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
        <div className="relative lg:col-span-7 lg:col-start-6">
          <div className="-mx-4 overflow-hidden sm:mx-0 sm:rounded-sm lg:-mr-[calc(max(0px,(100vw_-_72rem)/2)_+_1.5rem)] lg:rounded-r-none">
            <Photo
              name="red-pen"
              widths={[640, 1024, 1600]}
              width={1600}
              height={1066}
              sizes="(min-width: 1024px) 62vw, 100vw"
              alt="A hand writing in a notebook with a red pen"
              className="aspect-[3/2] h-auto w-full object-cover"
            />
          </div>
          <BrowserFrame className="relative mx-3 -mt-20 sm:mx-10 sm:-mt-32 lg:absolute lg:-bottom-16 lg:-left-12 lg:m-0 lg:w-[25rem]">
            <Screenshot
              name="product-fixes"
              widths={[560, 1120]}
              width={1120}
              height={PRODUCT.fixes}
              sizes="(min-width: 1024px) 400px, 92vw"
              alt="CheckON's suggested fixes for a sample posting: a pay range placeholder, and a sentence rewritten to drop a Canadian experience requirement"
            />
          </BrowserFrame>
        </div>
      </div>
    </section>
  )
}

/** One sentence from the sample posting, before and after the check. */
export function SampleFix() {
  return (
    <section
      aria-labelledby="sample-fix"
      className="relative isolate overflow-hidden bg-deep text-deep-foreground"
    >
      <Photo
        name="bg-pen"
        widths={[960, 1600]}
        width={1600}
        height={1201}
        sizes="100vw"
        alt="A fountain pen writing on lined paper"
        className="absolute inset-0 -z-20 h-full w-full object-cover object-[65%_center]"
      />
      <div className="absolute inset-0 -z-10 bg-deep/85" aria-hidden="true" />
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-28">
        <h2 id="sample-fix" className="text-sm font-medium text-deep-muted">
          One line from a sample posting, checked
        </h2>
        <dl className="mt-10 grid gap-x-10 gap-y-3 font-display text-[1.65rem] leading-snug sm:grid-cols-[7rem_1fr] sm:text-4xl">
          <dt className="font-site text-sm font-medium tracking-wide text-deep-muted uppercase sm:pt-3">
            Before
          </dt>
          <dd>
            <del className="decoration-[#e4836a] decoration-2">
              3+ years supervising in a warehouse, with Canadian experience
              required
            </del>
          </dd>
          <dt className="mt-6 font-sans text-sm font-medium tracking-wide text-deep-muted uppercase sm:mt-0 sm:pt-3">
            After
          </dt>
          <dd>
            <ins className="no-underline">
              3+ years supervising in a warehouse required
            </ins>
          </dd>
        </dl>
        <p className="mt-10 max-w-xl border-t border-white/15 pt-6 text-deep-muted sm:ml-[9.5rem]">
          CheckON's note: ask for the skill, not where it was gained. The rest
          of the sentence stays as written, and you decide whether to accept the
          change.
        </p>
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
    <section id="how" className="scroll-mt-16 bg-paper">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-28">
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-8">
          <div className="lg:col-span-5">
            <Kicker>How it works</Kicker>
            <Heading className="mt-5">
              From a pasted draft to a posting you can publish
            </Heading>
            <ol className="mt-10 border-t">
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
          <figure className="lg:col-span-6 lg:col-start-7">
            <BrowserFrame className="lg:sticky lg:top-24">
              <Screenshot
                name="product-findings"
                widths={[560, 1120]}
                width={1120}
                height={PRODUCT.findings}
                sizes="(min-width: 1024px) 540px, 92vw"
                alt="CheckON's rule-by-rule results for a sample posting: three items to fix, each quoting the sentence it is about"
              />
            </BrowserFrame>
            <figcaption className="mt-4 text-sm text-muted-foreground">
              Results for a sample posting: a warehouse shift supervisor in
              Mississauga.
            </figcaption>
          </figure>
        </div>
        <figure className="mt-16 lg:mt-24">
          <BrowserFrame className="mx-auto max-w-4xl">
            <Screenshot
              name="product-editor"
              widths={[560, 1120]}
              width={1120}
              height={PRODUCT.editor}
              sizes="(min-width: 1024px) 896px, 92vw"
              alt="The updated posting in CheckON's editor, with buttons to copy it formatted or as plain text"
            />
          </BrowserFrame>
          <figcaption className="mx-auto mt-4 max-w-4xl text-sm text-muted-foreground">
            Step 4: the updated posting opens in an editor, ready to copy.
          </figcaption>
        </figure>
      </div>
    </section>
  )
}

export function ForTeams() {
  const { contactAbout } = useContact()
  return (
    <section id="teams" className="scroll-mt-16">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-12 lg:gap-8">
        <div className="lg:sticky lg:top-24 lg:col-span-5 lg:self-start">
          <Kicker>Who it's for</Kicker>
          <Heading className="mt-5">
            For the people who write the postings
          </Heading>
        </div>
        <div className="space-y-14 lg:col-span-6 lg:col-start-7 lg:pt-2">
          <div>
            <h3 className="font-display text-3xl font-medium">
              HR at Ontario employers
            </h3>
            <p className="mt-4 text-muted-foreground">
              You're the HR generalist, or the whole HR team, at a business that
              hires every month. CheckON gives each posting a check before it
              goes up, and keeps the wording you chose.
            </p>
            <ul className="mt-6 space-y-3 border-l-2 border-brand pl-5">
              <li>
                Your company's details saved, so each check starts there{" "}
                <Soon />
              </li>
              <li>
                Pay range suggestions when a posting has none <Soon />
              </li>
              <li>A history of what you checked and approved</li>
            </ul>
          </div>
          <div>
            <h3 className="font-display text-3xl font-medium">
              Recruiting agencies
            </h3>
            <p className="mt-4 text-muted-foreground">
              You post for many clients, each with its own details. CheckON
              keeps them apart and gives you something to show each client.
            </p>
            <ul className="mt-6 space-y-3 border-l-2 border-brand pl-5">
              <li>
                A workspace per client, checked against that client's facts{" "}
                <Soon />
              </li>
              <li>
                A dated archive of every approved posting <Soon />
              </li>
              <li>
                A browser extension for any job form <Soon />, or a connection
                to your own systems
              </li>
            </ul>
            <Button
              className="mt-8"
              variant="outline"
              onClick={() => contactAbout("custom")}
            >
              Talk to us about your setup
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}

/** A feature we list but haven't built yet: say so wherever it appears. */
function Soon() {
  return (
    <span className="ml-1 inline-block rounded-full border px-1.5 py-px align-middle text-[0.7rem] font-medium whitespace-nowrap text-muted-foreground">
      Coming soon
    </span>
  )
}

interface Plan {
  name: string
  price: string
  period?: string
  note: string
  features: (string | { text: string; soon: true })[]
  cta: { label: string; interest?: Interest; checkout?: PlanId }
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
      { text: "Browser extension", soon: true },
    ],
    cta: { label: "Check a posting" },
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
      { text: "Company profile", soon: true },
      { text: "Pay range suggestions", soon: true },
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
      { text: "A workspace per client", soon: true },
      { text: "Archive of approved postings", soon: true },
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
              {plan.features.map((feature) =>
                typeof feature === "string" ? (
                  <li key={feature} className="flex gap-2">
                    <Check
                      className="mt-0.5 size-4 shrink-0 text-primary"
                      aria-hidden="true"
                    />
                    {feature}
                  </li>
                ) : (
                  <li
                    key={feature.text}
                    className="flex gap-2 text-muted-foreground"
                  >
                    <Clock
                      className="mt-0.5 size-4 shrink-0"
                      aria-hidden="true"
                    />
                    <span>
                      {feature.text} <Soon />
                    </span>
                  </li>
                ),
              )}
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
                <a href="#check">{plan.cta.label}</a>
              </Button>
            )}
          </div>
        ))}
      </div>
    </PricingSection>
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
    a: "No. It's processed by our AI provider to run the check and held for up to an hour while you review the results. We keep it only if you choose to share it when you report a problem. On a paid plan, we keep the date, job title and result of each check for your history, not the posting.",
  },
  {
    q: "What does the rewrite change?",
    a: "Only what compliance requires. Everything else stays exactly as you wrote it, and you approve each change before it's applied.",
  },
  {
    q: "What doesn't it check?",
    a: "It checks only the text you paste. An application form, a document the posting links to, and anything that happens after you post are outside the check.",
  },
  {
    q: "How do I get more checks or a custom setup?",
    a: "Pick Starter or Agency above, or contact us below for a custom setup. Plans are billed monthly and you can cancel anytime.",
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

/** A closing call to check a posting, beside a "Help wanted" sign. */
export function NextPosting() {
  return (
    <section
      aria-labelledby="next-posting"
      className="grid bg-deep text-deep-foreground lg:grid-cols-2"
    >
      <div className="relative h-60 sm:h-80 lg:order-last lg:h-auto">
        <Photo
          name="bg-help-wanted"
          widths={[960, 1440, 1920]}
          width={1920}
          height={1280}
          sizes="(min-width: 1024px) 50vw, 100vw"
          alt="A Help wanted sign taped inside a shop window"
          className="absolute inset-0 h-full w-full object-cover object-[55%_center]"
        />
      </div>
      <div className="px-4 py-16 sm:px-6 sm:py-24 lg:py-32 lg:pr-16 lg:pl-[max(1.5rem,calc((100vw-72rem)/2+1.5rem))]">
        <h2
          id="next-posting"
          className="max-w-lg font-display text-[2.125rem] leading-[1.08] font-medium tracking-[-0.015em] text-balance sm:text-5xl"
        >
          Hiring this week? Check the posting before it goes up.
        </h2>
        <p className="mt-5 max-w-md text-lg text-deep-muted">
          Paste it in, see what needs fixing and approve the changes. Free once
          a week, no sign-up.
        </p>
        <Button
          asChild
          size="lg"
          className="mt-8 bg-deep-foreground text-deep hover:bg-deep-foreground/90"
        >
          <a href="#check">Check a posting</a>
        </Button>
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

/** `home` prefixes the in-page anchors, for pages other than the checker. */
export function SiteFooter({ home = "" }: { home?: string }) {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 text-sm text-muted-foreground sm:flex-row sm:items-end sm:justify-between sm:px-6">
        <div className="space-y-3">
          <Brand href={`${home}#check`} />
          <p>Ontario job posting compliance. Not legal advice.</p>
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
    </footer>
  )
}
