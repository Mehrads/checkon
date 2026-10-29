import { Link } from "@tanstack/react-router"
import { ArrowRight, Check } from "lucide-react"
import { useEffect } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Button } from "@/components/ui/button"
import { loadAnalytics, track } from "@/lib/analytics"
import { type Lang, pageHead, SITE } from "@/lib/seo"
import { cn } from "@/lib/utils"
import { CopyButton } from "./CopyButton"
import { JsonLd, ORGANIZATION } from "./JsonLd"
import { Brand, SiteFooter } from "./Landing"
import { List, Part } from "./Legal"
import * as en from "./rules/en"
import * as fr from "./rules/fr"
import { Source } from "./rules/Source"
import {
  type Cite,
  RULE_IDS,
  type Rule,
  type RuleId,
  UPDATED,
  type Words,
} from "./rules/types"

const CONTENT: Record<Lang, { WORDS: Words; RULES: Record<RuleId, Rule> }> = {
  en,
  fr,
}

/** Every rule page's path, in both languages: the build renders each to HTML (src/prerender.tsx). */
export const RULE_PATHS = (["en", "fr"] as const).flatMap((lang) =>
  RULE_IDS.map((id) => CONTENT[lang].RULES[id].path),
)

/** A rule page's route options: the page, and its head with a link to the page in the other language. */
export function rulePage(id: RuleId, lang: Lang) {
  const rule = CONTENT[lang].RULES[id]
  const other = CONTENT[lang].WORDS.other.lang
  return {
    component: () => <RulePage id={id} lang={lang} />,
    head: () =>
      pageHead({
        path: rule.path,
        title: `${rule.title} | CheckON`,
        description: rule.description,
        lang,
        alternates: [{ lang: other, path: CONTENT[other].RULES[id].path }],
      }),
  }
}

/** What search engines read: the article, its questions, and where it sits on the site. */
function structured(rule: Rule, words: Words, lang: Lang) {
  const crumbs = [
    { name: words.home, path: "/check" },
    ...(words.guide ? [words.guide] : []),
    { name: rule.name, path: rule.path },
  ]
  return {
    "@graph": [
      {
        "@type": "Article",
        headline: rule.title,
        description: rule.description,
        inLanguage: `${lang}-CA`,
        dateModified: UPDATED,
        mainEntityOfPage: `${SITE}${rule.path}`,
        author: ORGANIZATION,
        publisher: ORGANIZATION,
      },
      {
        "@type": "FAQPage",
        inLanguage: `${lang}-CA`,
        mainEntity: rule.faq.map((item) => ({
          "@type": "Question",
          name: item.q,
          acceptedAnswer: { "@type": "Answer", text: item.a },
        })),
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
    ],
  }
}

function RulePage({ id, lang }: { id: RuleId; lang: Lang }) {
  useEffect(loadAnalytics, [])
  const words = CONTENT[lang].WORDS
  const rule = CONTENT[lang].RULES[id]
  const other = words.other.lang
  // The page in analytics events: the rule and its language, e.g. "rule-pay-fr"
  const page = `rule-${id}-${lang}`
  const copied = (item: string) => () => track("content-copy", { page, item })
  const cta = (name: string) => () => track("content-cta", { page, cta: name })
  return (
    <div
      lang={`${lang}-CA`}
      className="site min-h-svh bg-background text-foreground"
    >
      <JsonLd data={structured(rule, words, lang)} />
      <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Brand href="/check" />
          <div className="flex items-center gap-2">
            <Appearance />
            <Button asChild size="sm">
              <Link to="/check" hash="check" onClick={cta("header-check")}>
                {words.header}
              </Link>
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-12 px-4 py-16 sm:px-6 sm:py-20">
        <div className="space-y-4">
          <p className="text-sm font-medium text-primary">
            {words.guide ? (
              <Link
                to={words.guide.path}
                className="underline-offset-4 hover:underline"
              >
                {words.eyebrow}
              </Link>
            ) : (
              words.eyebrow
            )}
          </p>
          <h1 className="font-display text-4xl leading-tight font-medium tracking-[-0.015em] text-balance sm:text-5xl">
            {rule.h1}
          </h1>
          <p className="text-lg text-muted-foreground">{rule.intro}</p>
          <p className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span>{words.updated}</span>
            <Link
              to={CONTENT[other].RULES[id].path}
              hrefLang={`${other}-CA`}
              lang={`${other}-CA`}
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              {words.other.label}
            </Link>
          </p>
        </div>

        <section
          aria-labelledby="in-short"
          className="rounded-xl border bg-paper p-5 sm:p-6"
        >
          <h2 id="in-short" className="text-sm font-medium text-primary">
            {words.short}
          </h2>
          <ul className="mt-3 space-y-2">
            {rule.summary.map((line) => (
              <li key={line} className="flex gap-3">
                <Check
                  className="mt-1 size-4 shrink-0 text-primary"
                  aria-hidden="true"
                />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </section>

        <Part title={words.law}>
          <List>
            {rule.law.map((item, index) => (
              <li key={index}>
                {item.text} <Cites cites={item.cites} />
              </li>
            ))}
          </List>
        </Part>

        <Part title={rule.copy.heading}>
          {rule.copy.kind === "wording" ? (
            <div className="space-y-3">
              {rule.copy.items.map((item) => (
                <div key={item.text} className="rounded-lg border bg-card p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium">{item.label}</p>
                    <CopyButton
                      text={item.text}
                      label={`${words.copy}: ${item.label}`}
                      words={words}
                      onCopied={copied(item.label ?? "wording")}
                    />
                  </div>
                  <p className="mt-2 text-foreground">{item.text}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border bg-card p-4">
              <ul className="space-y-2">
                {rule.copy.items.map((item) => (
                  <li key={item.text} className="flex gap-3 text-foreground">
                    <span
                      className="mt-1 size-4 shrink-0 rounded-sm border border-primary/60"
                      aria-hidden="true"
                    />
                    {item.text}
                  </li>
                ))}
              </ul>
              <div className="mt-4">
                <CopyButton
                  text={rule.copy.items
                    .map((item) => `- ${item.text}`)
                    .join("\n")}
                  label={words.copyAll}
                  words={words}
                  onCopied={copied("checklist")}
                />
              </div>
            </div>
          )}
        </Part>

        <Part title={words.example}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Example label={words.before} text={rule.example.before} />
            <Example label={words.after} text={rule.example.after} fixed />
          </div>
          <p>{rule.example.note}</p>
        </Part>

        <Part title={words.checkHeading}>
          <p>{rule.check}</p>
          {words.checkNote && <p className="text-sm">{words.checkNote}</p>}
          <div className="pt-2">
            <Button asChild size="lg">
              <Link to="/check" hash="check" onClick={cta("check")}>
                {words.checkButton} <ArrowRight />
              </Link>
            </Button>
          </div>
        </Part>

        <Part title={words.scope.heading}>
          <p>
            {words.scope.text} <Cites cites={words.scope.cites} />
          </p>
          {words.guide && (
            <p>
              <Link
                to={words.guide.path}
                className="text-primary underline-offset-4 hover:underline"
              >
                {words.guide.name}
              </Link>
            </p>
          )}
        </Part>

        <section className="space-y-3">
          <h2 className="font-display text-2xl font-medium tracking-[-0.01em]">
            {words.faq}
          </h2>
          <div className="border-t">
            {rule.faq.map((item) => (
              <details key={item.q} className="group border-b py-4">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
                  {item.q}
                  <span
                    className="text-xl text-primary transition-transform group-open:rotate-45"
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

        <Part title={words.rules}>
          <RuleLinks lang={lang} exclude={id} />
        </Part>

        <p className="border-t pt-6 text-sm text-muted-foreground">
          {words.source}
        </p>
      </main>
      <SiteFooter home="/check" note={words.footer} />
    </div>
  )
}

function Cites({ cites }: { cites: Cite[] }) {
  return (
    <span className="text-sm">
      (
      {cites.map((cite, index) => (
        <span key={cite.label}>
          {index > 0 && "; "}
          <span className="whitespace-nowrap">
            <Source href={cite.href}>{cite.label}</Source>
          </span>
        </span>
      ))}
      )
    </span>
  )
}

function Example({
  label,
  text,
  fixed = false,
}: {
  label: string
  text: string
  fixed?: boolean
}) {
  return (
    <figure
      className={cn(
        "rounded-lg border bg-card p-4",
        fixed && "border-primary/50",
      )}
    >
      <figcaption className="text-xs font-medium tracking-wide uppercase">
        {label}
      </figcaption>
      <p className="mt-2 whitespace-pre-line text-foreground">{text}</p>
    </figure>
  )
}

/** Links to the rule pages in one language, without the page you're on. */
export function RuleLinks({
  lang,
  exclude,
  className,
}: {
  lang: Lang
  exclude?: RuleId
  className?: string
}) {
  const rules = CONTENT[lang].RULES
  return (
    <ul className={cn("grid gap-3 sm:grid-cols-2", className)}>
      {RULE_IDS.filter((id) => id !== exclude).map((id) => (
        <li key={id}>
          <Link
            to={rules[id].path}
            className="group flex h-full flex-col rounded-lg border bg-card p-4 transition-colors hover:border-primary/60"
          >
            <span className="flex items-center justify-between gap-3 font-medium text-foreground">
              {rules[id].name}
              <ArrowRight
                className="size-4 shrink-0 text-primary transition-transform group-hover:translate-x-0.5"
                aria-hidden="true"
              />
            </span>
            <span className="mt-1 text-sm text-muted-foreground">
              {rules[id].blurb}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
