import type { Report, RuleResult, Verdict } from "@/client"
import { cn } from "@/lib/utils"
import { AfterPosting } from "./AfterPosting"
import { FeedbackButtons } from "./Feedback"
import { ruleName, VERDICT_TEXT } from "./labels"
import { host } from "./PostingLink"
import { VerdictIcon } from "./StatusIcon"

const ORDER: Verdict[] = [
  "fail",
  "warning",
  "needs_input",
  "pass",
  "not_applicable",
]

const QUOTE_TONE: Partial<Record<Verdict, string>> = {
  fail: "border-red-500 bg-red-50 dark:bg-red-950/30",
  warning: "border-amber-500 bg-amber-50 dark:bg-amber-950/30",
  needs_input: "border-sky-500 bg-sky-50 dark:bg-sky-950/30",
}

interface FindingsProps {
  checkId: string
  report: Report
  text: string // the normalised posting the evidence spans point into
  formText?: string | null // the application form, once checked; its findings point into it
  url?: string | null // the page the posting was read from, for a check by link
}

function Finding({
  checkId,
  result,
  text,
  target,
}: {
  checkId: string
  result: RuleResult
  text: string
  target: string
}) {
  const quotes = result.verdict === "pass" ? [] : (result.evidence ?? [])
  return (
    <li className="group flex gap-3 px-5 py-4">
      <VerdictIcon verdict={result.verdict} className="mt-0.5" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <p className="font-medium">{ruleName(result.rule)}</p>
          <span className="text-xs font-medium text-muted-foreground">
            {VERDICT_TEXT[result.verdict]}
          </span>
        </div>
        <p className="text-sm text-muted-foreground">{result.message}</p>
        <p className="text-xs text-muted-foreground/80">{result.citation}</p>
        {quotes.map(([start, end]) => (
          <blockquote
            key={`${start}-${end}`}
            className={cn(
              "rounded-r-md border-l-2 px-3 py-1.5 text-sm whitespace-pre-line",
              QUOTE_TONE[result.verdict],
            )}
          >
            {text.slice(start, end)}
          </blockquote>
        ))}
        <div className="opacity-60 transition-opacity group-hover:opacity-100">
          <FeedbackButtons checkId={checkId} kind="finding" target={target} />
        </div>
      </div>
    </li>
  )
}

const sorted = (results: RuleResult[]) =>
  [...results].sort(
    (a, b) => ORDER.indexOf(a.verdict) - ORDER.indexOf(b.verdict),
  )

/** What the check read, and what it couldn't: "Checked: … Not checked: …". */
export function checkedLine(url: string | null | undefined, form: boolean) {
  const posting = url ? `the posting at ${host(url)}` : "the posting's text"
  const missed = [
    ...(form ? [] : ["your application form"]),
    "documents the posting links to",
    "what happens after you post",
  ]
  const list =
    missed.length > 2
      ? `${missed.slice(0, -1).join(", ")}, and ${missed[missed.length - 1]}`
      : missed.join(" and ")
  return `Checked: ${posting}${form ? " and your application form" : ""}. Not checked: ${list}.`
}

/** Every rule's verdict, problems first, each pointing at the sentence it is about; the application form's, once
 * checked, pointing at its questions; then what happens after posting and what the check didn't look at. */
export function Findings({
  checkId,
  report,
  text,
  formText,
  url,
}: FindingsProps) {
  const form = formText ? sorted(report.form_results ?? []) : []
  return (
    <section
      aria-labelledby="findings"
      className="rounded-xl border bg-card shadow-sm"
    >
      <header className="border-b px-5 py-4">
        <h2 id="findings" className="font-semibold">
          Rule by rule
        </h2>
        <p className="text-sm text-muted-foreground">
          Each verdict applies the rule to what your posting says.
        </p>
      </header>
      <ul className="divide-y">
        {sorted(report.results).map((result) => (
          <Finding
            key={result.rule}
            checkId={checkId}
            result={result}
            text={text}
            target={result.rule}
          />
        ))}
      </ul>
      {formText && form.length > 0 && (
        <>
          <h3 className="border-t bg-muted/40 px-5 py-3 text-sm font-semibold">
            Application form
          </h3>
          <ul className="divide-y border-t">
            {form.map((result) => (
              <Finding
                key={result.rule}
                checkId={checkId}
                result={result}
                text={formText}
                target={`${result.rule}:form`}
              />
            ))}
          </ul>
        </>
      )}
      <AfterPosting reminders={report.reminders ?? []} />
      <p className="border-t px-5 py-3 text-xs text-muted-foreground">
        {checkedLine(url, Boolean(formText))}
      </p>
    </section>
  )
}
