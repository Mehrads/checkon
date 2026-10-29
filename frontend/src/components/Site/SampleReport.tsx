import { Link } from "@tanstack/react-router"
import { ArrowRight, Check } from "lucide-react"
import { type SyntheticEvent, useEffect, useRef } from "react"

import type { Patch } from "@/client"
import { ruleName } from "@/components/Check/labels"
import { StatusLabel, VerdictIcon } from "@/components/Check/StatusIcon"
import { Button } from "@/components/ui/button"
import { track } from "@/lib/analytics"
import { Heading, Kicker } from "./Landing"
import {
  SAMPLE_CHECKED,
  SAMPLE_FINAL,
  SAMPLE_FINDINGS,
  SAMPLE_FIXES,
  SAMPLE_LOCATION,
  SAMPLE_PASSED,
  SAMPLE_POSTING,
  SAMPLE_RULE_PACK,
  SAMPLE_TITLE,
  type SampleFinding,
  type SampleFix,
} from "./sample"

// Who wrote each fix, in plain words (the wording library isn't signed off yet, so not "approved wording")
const WRITER: Record<Patch["writer"], string> = {
  template: "Placeholder",
  code: "Calculated",
  wording_library: "Standard wording",
  llm: "Rewritten, then checked again",
}

function Finding({ finding }: { finding: SampleFinding }) {
  return (
    <li className="flex gap-3 px-5 py-4">
      <VerdictIcon verdict={finding.verdict} className="mt-0.5" />
      <div className="min-w-0 space-y-2">
        <p>
          <span className="font-medium">{ruleName(finding.rule)}.</span>{" "}
          <span className="text-muted-foreground">{finding.message}</span>
        </p>
        {finding.quote && (
          <blockquote className="border-l-2 border-red-500/70 pl-3 text-sm">
            “{finding.quote}”
          </blockquote>
        )}
        {finding.question && (
          <div className="space-y-1 rounded-lg bg-muted/60 p-3 text-sm">
            <p>
              <span className="font-medium">CheckON asked:</span>{" "}
              {finding.question}
            </p>
            <p>
              <span className="font-medium">Answer:</span> {finding.answer}.
              {finding.answered && (
                <span className="text-muted-foreground">
                  {" "}
                  {finding.answered}
                </span>
              )}
            </p>
          </div>
        )}
        <p className="text-xs text-muted-foreground">{finding.citation}</p>
      </div>
    </li>
  )
}

function Fix({ fix }: { fix: SampleFix }) {
  return (
    <li className="space-y-2 px-5 py-4 text-sm">
      <p className="flex flex-wrap items-baseline justify-between gap-x-3">
        <span className="font-medium">{ruleName(fix.rule)}</span>
        <span className="text-xs text-muted-foreground">
          {WRITER[fix.writer]}
        </span>
      </p>
      {fix.before && (
        <p>
          <del className="text-muted-foreground decoration-red-500/70">
            {fix.before}
          </del>
        </p>
      )}
      {fix.options ? (
        <ul className="space-y-1" aria-label="Ranges offered">
          {fix.options.map((option) => (
            <li key={option} className="flex items-center gap-2">
              {option === fix.after ? (
                <Check
                  className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400"
                  aria-label="Picked"
                />
              ) : (
                <span className="size-4 shrink-0" aria-hidden="true" />
              )}
              <span
                className={
                  option === fix.after ? "font-medium" : "text-muted-foreground"
                }
              >
                {option}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p>
          <ins className="font-medium no-underline">
            {fix.before ? "" : "Added: "}
            {fix.after}
          </ins>
        </p>
      )}
    </li>
  )
}

/** A real result on a made-up posting (sample.ts), so a visitor without a posting at hand sees what a check gives:
 * the verdicts with their sentences and sources, the questions, the fixes, and the posting once they're approved. */
export function SampleReport() {
  const section = useRef<HTMLElement>(null)
  // Counted once a visit, when most of the section has been on screen
  useEffect(() => {
    const element = section.current
    if (!element || !("IntersectionObserver" in window)) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          track("sample-view")
          observer.disconnect()
        }
      },
      { threshold: 0.25 },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  const opened =
    (part: string) => (event: SyntheticEvent<HTMLDetailsElement>) => {
      if (event.currentTarget.open) track("sample-open", { part })
    }

  return (
    <section
      ref={section}
      id="sample"
      aria-labelledby="sample-heading"
      className="scroll-mt-16 bg-paper"
    >
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-12 lg:gap-8">
        <div className="lg:sticky lg:top-24 lg:col-span-5 lg:self-start">
          <Kicker>Sample result</Kicker>
          <Heading id="sample-heading" className="mt-5">
            A real result, on a sample posting
          </Heading>
          <p className="mt-6 text-muted-foreground">
            This is what CheckON returned for a made-up warehouse posting. Each
            verdict quotes the line it's about and names its source. Where the
            answer depends on something only the employer knows, it asks.
          </p>
          <p className="mt-4 text-muted-foreground">
            It suggested four fixes, each one to keep or drop. With all four
            approved, the posting met the rules.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link
                to="/check"
                hash="check"
                onClick={() => track("sample-check")}
              >
                Check your own posting <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/accuracy" onClick={() => track("sample-accuracy")}>
                How accurate is it?
              </Link>
            </Button>
          </div>
        </div>

        <div className="min-w-0 space-y-4 lg:col-span-7">
          <article
            aria-label="Sample result"
            className="overflow-hidden rounded-2xl border bg-card shadow-sm"
          >
            <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 border-b px-5 py-4">
              <div>
                <h3 className="font-semibold">{SAMPLE_TITLE}</h3>
                <p className="text-sm text-muted-foreground">
                  {SAMPLE_LOCATION} · as pasted
                </p>
              </div>
              <span className="text-sm">
                <StatusLabel status="not_compliant" />
              </span>
            </header>
            <ol className="divide-y">
              {SAMPLE_FINDINGS.map((finding) => (
                <Finding key={finding.rule} finding={finding} />
              ))}
            </ol>
            <p className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t px-5 py-3 text-sm text-muted-foreground">
              <span>Also checked:</span>
              {SAMPLE_PASSED.map((rule) => (
                <span key={rule} className="inline-flex items-center gap-1.5">
                  <VerdictIcon verdict="pass" className="size-4" />
                  {ruleName(rule)}
                </span>
              ))}
            </p>

            <h4 className="border-t bg-muted/40 px-5 py-3 text-sm font-semibold">
              Suggested fixes
            </h4>
            <ol className="divide-y border-t">
              {SAMPLE_FIXES.map((fix) => (
                <Fix key={fix.rule} fix={fix} />
              ))}
            </ol>

            <div className="space-y-3 border-t px-5 py-4">
              <p className="text-sm">
                <StatusLabel status="compliant" />
                <span className="text-muted-foreground">
                  {" "}
                  after the four fixes were approved.
                </span>
              </p>
              <details className="group text-sm" onToggle={opened("finished")}>
                <summary className="cursor-pointer font-medium text-primary">
                  See the finished posting
                </summary>
                <pre className="mt-3 rounded-lg border bg-background p-4 font-site leading-relaxed whitespace-pre-wrap">
                  {SAMPLE_FINAL}
                </pre>
              </details>
              <details className="group text-sm" onToggle={opened("pasted")}>
                <summary className="cursor-pointer font-medium text-primary">
                  See the posting as it was pasted
                </summary>
                <pre className="mt-3 rounded-lg border bg-background p-4 font-site leading-relaxed whitespace-pre-wrap">
                  {SAMPLE_POSTING}
                </pre>
              </details>
            </div>
          </article>
          <p className="text-xs text-muted-foreground">
            Checked by CheckON on {SAMPLE_CHECKED}, rule version{" "}
            {SAMPLE_RULE_PACK}, with both questions answered "yes". The posting
            is made up for this example and names no employer. A result depends
            on the posting and your answers.
          </p>
        </div>
      </div>
    </section>
  )
}
