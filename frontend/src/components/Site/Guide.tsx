import { Link } from "@tanstack/react-router"
import { ArrowRight } from "lucide-react"
import { type ReactNode, useEffect } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Button } from "@/components/ui/button"
import { loadAnalytics, track } from "@/lib/analytics"
import { pageHead, SITE } from "@/lib/seo"
import { cn } from "@/lib/utils"
import { CopyButton } from "./CopyButton"
import { GUIDE_IDS, GUIDES, GUIDES_UPDATED, type GuideId } from "./guides"
import { JsonLd, ORGANIZATION } from "./JsonLd"
import { Brand, SiteFooter } from "./Landing"
import { Part } from "./Legal"
import { Source } from "./rules/Source"
import { SOURCES } from "./rules/types"

export const REQUIREMENTS = {
  name: "Ontario job posting requirements",
  path: "/ontario-job-posting-requirements",
}

export interface Question {
  q: string
  a: string
}

/** A guide's head: its title (before " | CheckON"), description and address. */
export function guideHead(id: GuideId, title: string, description: string) {
  return () =>
    pageHead({
      path: GUIDES[id].path,
      title: `${title} | CheckON`,
      description,
    })
}

/** What search engines read: the article, where it sits on the site, and its questions. */
function structured(
  id: GuideId,
  title: string,
  description: string,
  faq: Question[],
) {
  const guide = GUIDES[id]
  const crumbs = [
    { name: "CheckON", path: "/check" },
    REQUIREMENTS,
    { name: guide.name, path: guide.path },
  ]
  return {
    "@graph": [
      {
        "@type": "Article",
        headline: title,
        description,
        inLanguage: "en-CA",
        dateModified: GUIDES_UPDATED,
        mainEntityOfPage: `${SITE}${guide.path}`,
        author: ORGANIZATION,
        publisher: ORGANIZATION,
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: crumbs.map((crumb, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: crumb.name,
          item: `${SITE}${crumb.path}`,
        })),
      },
      ...(faq.length
        ? [
            {
              "@type": "FAQPage",
              inLanguage: "en-CA",
              mainEntity: faq.map((item) => ({
                "@type": "Question",
                name: item.q,
                acceptedAnswer: { "@type": "Answer", text: item.a },
              })),
            },
          ]
        : []),
    ],
  }
}

/** A content page: the site's header, the title block, the page, its questions, the other guides and the
 * footer. Prints without the header, footer and buttons. */
export function GuidePage({
  id,
  title,
  description,
  h1,
  intro,
  updated = "Updated October 28, 2026. A summary, not legal advice.",
  faq = [],
  children,
}: {
  id: GuideId
  title: string
  description: string
  h1: string
  intro: ReactNode
  updated?: string
  faq?: Question[]
  children: ReactNode
}) {
  useEffect(loadAnalytics, [])
  const page = GUIDES[id].page
  return (
    <div className="site min-h-svh bg-background text-foreground">
      <JsonLd data={structured(id, title, description, faq)} />
      <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur print:hidden">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Brand href="/check" />
          <div className="flex items-center gap-2">
            <Appearance />
            <Button asChild size="sm">
              <Link
                to="/check"
                hash="check"
                onClick={() =>
                  track("content-cta", { page, cta: "header-check" })
                }
              >
                Check a posting
              </Link>
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-12 px-4 py-16 sm:px-6 sm:py-20 print:py-0">
        <div className="space-y-4">
          <p className="text-sm font-medium text-primary">
            <Link
              to={REQUIREMENTS.path}
              className="underline-offset-4 hover:underline"
            >
              Ontario job posting rules
            </Link>
          </p>
          <h1 className="font-display text-4xl leading-tight font-medium tracking-[-0.015em] text-balance sm:text-5xl">
            {h1}
          </h1>
          <div className="space-y-3 text-lg text-muted-foreground">{intro}</div>
          <p className="text-sm text-muted-foreground">{updated}</p>
        </div>

        {children}

        {faq.length > 0 && (
          <section className="space-y-3">
            <h2 className="font-display text-2xl font-medium tracking-[-0.01em]">
              Questions people ask
            </h2>
            <div className="border-t">
              {faq.map((item) => (
                <details key={item.q} className="group border-b py-4">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
                    {item.q}
                    <span
                      className="text-xl text-primary transition-transform group-open:rotate-45 print:hidden"
                      aria-hidden="true"
                    >
                      +
                    </span>
                  </summary>
                  <p className="mt-2 text-muted-foreground">{item.a}</p>
                </details>
              ))}
            </div>
          </section>
        )}

        <div className="print:hidden">
          <Part title="More guides">
            <GuideLinks exclude={id} />
          </Part>
        </div>

        <p className="border-t pt-6 text-sm text-muted-foreground">
          Sources: the{" "}
          <Source href={SOURCES.en.act}>Employment Standards Act, 2000</Source>{" "}
          (ESA), Part III.1 and s. 15,{" "}
          <Source href={SOURCES.en.reg}>O. Reg. 476/24</Source> and the
          Government of Ontario's{" "}
          <Source href={SOURCES.en.guide}>
            guide to the job posting requirements
          </Source>
          . This page summarises them and isn't legal advice; for your
          situation, talk to an employment lawyer.
        </p>
      </main>
      <div className="print:hidden">
        <SiteFooter home="/check" />
      </div>
    </div>
  )
}

/** The section that sends a reader to the checker (and any other `actions`), with its analytics event. */
export function GuideCta({
  id,
  title,
  children,
  label = "Check a posting free",
  hash = "check",
  cta = "check",
  more,
}: {
  id: GuideId
  title: string
  children: ReactNode
  label?: string
  hash?: string
  cta?: string
  more?: ReactNode
}) {
  return (
    <section className="space-y-3 rounded-xl border bg-paper p-5 sm:p-6 print:hidden">
      <h2 className="font-display text-2xl font-medium tracking-[-0.01em]">
        {title}
      </h2>
      <div className="space-y-3 text-muted-foreground">{children}</div>
      <div className="flex flex-wrap gap-3 pt-2">
        <Button asChild size="lg">
          <Link
            to="/check"
            hash={hash}
            onClick={() => track("content-cta", { page: GUIDES[id].page, cta })}
          >
            {label} <ArrowRight />
          </Link>
        </Button>
        {more}
      </div>
    </section>
  )
}

/** A second button in a GuideCta: another page on the site, with its own analytics event. */
export function GuideButton({
  id,
  to,
  hash,
  cta,
  children,
}: {
  id: GuideId
  to: string
  hash?: string
  cta: string
  children: ReactNode
}) {
  return (
    <Button asChild size="lg" variant="outline">
      <Link
        to={to}
        hash={hash}
        onClick={() => track("content-cta", { page: GUIDES[id].page, cta })}
      >
        {children}
      </Link>
    </Button>
  )
}

/** A block of text to copy (a template, a checklist), shown as it will paste. */
export function CopyBlock({
  id,
  item,
  label,
  text,
  title,
}: {
  id: GuideId
  item: string
  label: string
  text: string
  title: string
}) {
  return (
    <figure className="rounded-lg border bg-card">
      <figcaption className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <span className="text-sm font-medium text-foreground">{title}</span>
        <CopyButton
          text={text}
          label={label}
          onCopied={() =>
            track("content-copy", { page: GUIDES[id].page, item })
          }
        />
      </figcaption>
      <pre className="overflow-x-auto p-4 font-site text-sm leading-relaxed whitespace-pre-wrap text-foreground">
        {text}
      </pre>
    </figure>
  )
}

/** Links to the guides, without the page you're on. */
export function GuideLinks({
  exclude,
  className,
}: {
  exclude?: GuideId
  className?: string
}) {
  return (
    <ul className={cn("grid gap-3 sm:grid-cols-2", className)}>
      {GUIDE_IDS.filter((id) => id !== exclude).map((id) => (
        <li key={id}>
          <Link
            to={GUIDES[id].path}
            className="group flex h-full flex-col rounded-lg border bg-card p-4 transition-colors hover:border-primary/60"
          >
            <span className="flex items-center justify-between gap-3 font-medium text-foreground">
              {GUIDES[id].name}
              <ArrowRight
                className="size-4 shrink-0 text-primary transition-transform group-hover:translate-x-0.5"
                aria-hidden="true"
              />
            </span>
            <span className="mt-1 text-sm text-muted-foreground">
              {GUIDES[id].blurb}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
