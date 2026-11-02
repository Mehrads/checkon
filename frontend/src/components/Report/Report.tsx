import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ArrowRight, Check, ExternalLink } from "lucide-react"

import {
  type ReportFinding as Finding,
  type PostingOut,
  type ReportOut,
  ReportsService,
  type Status,
} from "@/client"
import { shortAddress } from "@/components/Audit/summary"
import { FREE_ACCOUNT_CHECKS, formatDay } from "@/components/Billing/UsageMeter"
import { ruleName } from "@/components/Check/labels"
import { StatusLabel, VerdictIcon } from "@/components/Check/StatusIcon"
import { RULES } from "@/components/Site/rules/en"
import type { RuleId } from "@/components/Site/rules/types"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { isLoggedIn } from "@/hooks/useAuth"
import { apiMessage } from "@/hooks/useBilling"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"

// The rule page that explains each finding, with wording to copy
const RULE_PAGE: Record<string, RuleId> = {
  "ON-PAY-01": "pay",
  "ON-PAY-02": "pay",
  "ON-CEX-01": "cex",
  "ON-AI-01": "ai",
  "ON-VAC-01": "vacancy",
  "ON-INT-01": "interview",
  "ON-REC-01": "records",
}

// What no posting shows: the report asks instead
const PROCESS: { rule: string; question: string; reminder: string }[] = [
  {
    rule: "ON-INT-01",
    question:
      "Do you tell every interviewed applicant, within 45 days of their last interview, whether a hiring decision has been made?",
    reminder:
      "Since January 1, 2026, that's required: in person, in writing, or by email, text or your applicant portal.",
  },
  {
    rule: "ON-REC-01",
    question:
      "Do you keep each posting, its application form and what you told interviewed applicants for 3 years?",
    reminder:
      "Keep every version of the posting and its form for 3 years after it comes down, and what you told each interviewed applicant for 3 years.",
  },
]

const ANSWERS = [
  ["yes", "Yes"],
  ["no", "No"],
  ["unsure", "Not sure"],
] as const

export const reportKey = (token: string) => ["report", token]

/** "Acme's", "Achievers'". */
function possessive(name: string): string {
  return name.endsWith("s") ? `${name}'` : `${name}'s`
}

/** What "may need changes" counts, here and in the outreach note: a needs_input finding only asks a question. */
function needsFix(posting: PostingOut): boolean {
  return (
    [...posting.findings, ...posting.form_findings].some((f) =>
      ["fail", "warning"].includes(f.verdict),
    ) || posting.form_status === "not_compliant"
  )
}

/** Anything to act on, a question to answer included. */
function hasFindings(posting: PostingOut): boolean {
  return (
    posting.findings.length + posting.form_findings.length > 0 ||
    needsFix(posting)
  )
}

function RuleLink({ rule }: { rule: string }) {
  const page = RULE_PAGE[rule]
  if (!page) return null
  return (
    <a
      href={RULES[page].path}
      target="_blank"
      rel="noreferrer"
      className="text-sm whitespace-nowrap underline underline-offset-4"
    >
      What the rule asks
    </a>
  )
}

function Findings({ findings }: { findings: Finding[] }) {
  return (
    <ul className="space-y-3">
      {findings.map((finding) => (
        <li key={finding.rule} className="flex gap-2 text-sm">
          <VerdictIcon verdict={finding.verdict} className="mt-0.5 size-4" />
          <div className="min-w-0 space-y-1">
            <p>
              <span className="font-medium">{ruleName(finding.rule)}.</span>{" "}
              <span className="text-muted-foreground">{finding.message}</span>{" "}
              <RuleLink rule={finding.rule} />
            </p>
            {(finding.quotes ?? []).map((quote) => (
              <blockquote
                key={quote}
                className="border-l-2 border-amber-400 pl-3 text-muted-foreground italic"
              >
                "{quote}"
              </blockquote>
            ))}
          </div>
        </li>
      ))}
    </ul>
  )
}

/** Where "Fix this posting" goes: the checker with the posting's link, or a free account first. */
function FixButton({ posting, token }: { posting: PostingOut; token: string }) {
  if (isLoggedIn()) {
    return (
      <Button asChild size="sm">
        <Link to="/" search={{ url: posting.url }}>
          Fix this posting <ArrowRight />
        </Link>
      </Button>
    )
  }
  return (
    <Button asChild size="sm" variant="outline">
      <Link to="/signup" search={{ report: token }}>
        Get the fix free <ArrowRight />
      </Link>
    </Button>
  )
}

function PostingCard({
  posting,
  token,
}: {
  posting: PostingOut
  token: string
}) {
  const checked = !["refused", "failed"].includes(posting.status)
  return (
    <li className="space-y-4 px-5 py-5 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <a
            href={posting.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-start gap-1 font-medium underline-offset-4 hover:underline"
          >
            {posting.title}
            <ExternalLink
              className="mt-1 size-3 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
          </a>
          <p className="text-sm text-muted-foreground">
            {posting.location ?? "No location given"}
          </p>
        </div>
        <div className="text-sm">
          {posting.status === "not_compliant" ? (
            <span className="inline-flex items-center gap-1.5">
              <VerdictIcon verdict="fail" className="size-4" />
              May need changes
            </span>
          ) : checked ? (
            <StatusLabel status={posting.status as Status} />
          ) : (
            <span className="text-muted-foreground">Not checked</span>
          )}
        </div>
      </div>
      {posting.note && (
        <p className="text-sm text-muted-foreground">{posting.note}</p>
      )}
      {posting.findings.length > 0 && <Findings findings={posting.findings} />}
      {posting.form_findings.length > 0 && (
        <div className="space-y-3 rounded-lg bg-muted/50 p-4">
          <p className="text-sm font-medium">Its application form</p>
          <Findings findings={posting.form_findings} />
        </div>
      )}
      {checked && !hasFindings(posting) && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Check className="size-4 text-primary" aria-hidden="true" />
          Nothing to fix
          {posting.form_status === "compliant" &&
            ", the application form included"}
          .
        </p>
      )}
      {hasFindings(posting) &&
        posting.form_status === "compliant" &&
        posting.form_findings.length === 0 && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Check className="size-4 text-primary" aria-hidden="true" />
            Its application form: nothing to fix.
          </p>
        )}
      {hasFindings(posting) && <FixButton posting={posting} token={token} />}
    </li>
  )
}

function Checklist({ report }: { report: ReportOut }) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const answer = useMutation({
    mutationFn: async (answers: Record<string, string>) =>
      (
        await ReportsService.answerChecklist({
          path: { token: report.token },
          body: { answers: answers as Record<string, "yes" | "no" | "unsure"> },
        })
      ).data,
    onSuccess: (data) =>
      queryClient.setQueryData(reportKey(report.token), data),
    onError: (error) =>
      showErrorToast(apiMessage(error, "We couldn't save your answer.")),
  })
  return (
    <ul className="divide-y rounded-xl border bg-card shadow-sm">
      {PROCESS.map((item) => {
        const given = report.checklist[item.rule]
        return (
          <li key={item.rule} className="space-y-3 px-5 py-5 sm:px-6">
            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">{item.question}</legend>
              <div className="flex flex-wrap gap-2">
                {ANSWERS.map(([value, label]) => (
                  <Button
                    key={value}
                    size="sm"
                    variant={given === value ? "default" : "outline"}
                    aria-pressed={given === value}
                    disabled={answer.isPending}
                    onClick={() => answer.mutate({ [item.rule]: value })}
                  >
                    {label}
                  </Button>
                ))}
              </div>
            </fieldset>
            {given && given !== "yes" && (
              <p className="text-sm text-muted-foreground">
                {item.reminder} <RuleLink rule={item.rule} />
              </p>
            )}
          </li>
        )
      })}
    </ul>
  )
}

/** The next step for the company: save the report to an account, or open it there. */
function NextStep({ report }: { report: ReportOut }) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const save = useMutation({
    mutationFn: async () =>
      (await ReportsService.saveReport({ path: { token: report.token } })).data,
    onSuccess: (data) => {
      queryClient.setQueryData(reportKey(report.token), data)
      queryClient.invalidateQueries({ queryKey: ["reports"] })
    },
    onError: (error) =>
      showErrorToast(apiMessage(error, "We couldn't save the report.")),
  })
  if (report.mine) {
    return (
      <p className="flex items-center gap-2 text-sm">
        <Check className="size-4 text-primary" aria-hidden="true" />
        Saved to your account.{" "}
        <Link to="/reports" className="underline underline-offset-4">
          Your reports
        </Link>
      </p>
    )
  }
  if (report.saved) {
    return (
      <p className="text-sm text-muted-foreground">
        This report is saved to another CheckON account.
      </p>
    )
  }
  if (isLoggedIn()) {
    return (
      <LoadingButton loading={save.isPending} onClick={() => save.mutate()}>
        Save to my account
      </LoadingButton>
    )
  }
  return (
    <div className="flex flex-wrap gap-3">
      <Button asChild>
        <Link to="/signup" search={{ report: report.token }}>
          Create a free account <ArrowRight />
        </Link>
      </Button>
      <Button asChild variant="outline">
        <Link
          to="/login"
          search={{ redirect: `/report/${report.token}?save=1` }}
        >
          Log in
        </Link>
      </Button>
    </div>
  )
}

const STEPS = [
  ["See what each posting may miss", "Below, with the words we read."],
  [
    "Get the fixes",
    `A free account checks ${FREE_ACCOUNT_CHECKS} postings a month and writes each fix for you to approve.`,
  ],
  [
    "Publish and keep records",
    "Copy the fixed posting into your job board, and answer the two questions at the end.",
  ],
]

/** An outreach report: what a company's open Ontario postings may miss, and the way from here to fixed postings. */
export function Report({ report }: { report: ReportOut }) {
  const toFix = report.postings.filter(needsFix).length
  const forms = report.postings.filter(
    (p) => p.form_status === "not_compliant",
  ).length
  const formsRead = report.postings.some((p) => p.form_status !== null)
  const tiles: [number, string][] = [
    [report.postings.length, "open Ontario postings checked"],
    [toFix, "may need changes"],
    ...(formsRead
      ? [
          [
            forms,
            forms === 1
              ? "application form asks for Canadian experience"
              : "application forms ask for Canadian experience",
          ] as [number, string],
        ]
      : []),
  ]
  return (
    <div className="mx-auto max-w-4xl space-y-12 px-4 py-12 sm:px-6 sm:py-16">
      <header className="space-y-4">
        <p className="text-sm font-medium text-muted-foreground">
          CheckON report · {formatDay(report.created_at)}
        </p>
        <h1 className="font-display text-[2.125rem] leading-[1.08] font-medium tracking-[-0.015em] text-balance sm:text-5xl">
          {possessive(report.company)} open job postings and Ontario's posting
          rules
        </h1>
        <p className="text-muted-foreground">
          We read the postings on{" "}
          <a
            href={report.url}
            target="_blank"
            rel="noreferrer"
            className="underline underline-offset-4"
          >
            {shortAddress(report.url)}
          </a>{" "}
          for work in Ontario
          {report.outside_ontario > 0 &&
            ` (and left out ${report.outside_ontario} for work elsewhere)`}{" "}
          and checked each against the rules that took effect on January 1,
          2026.
        </p>
      </header>

      <div
        className={cn(
          "grid gap-px overflow-hidden rounded-xl border bg-border",
          tiles.length === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2",
        )}
      >
        {tiles.map(([n, label]) => (
          <div key={label} className="bg-card p-5">
            <p className="font-display text-4xl font-medium tabular-nums">
              {n}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">{label}</p>
          </div>
        ))}
      </div>

      <section aria-labelledby="steps" className="space-y-4">
        <h2 id="steps" className="font-display text-2xl font-medium">
          From here to postings that comply
        </h2>
        <ol className="grid gap-4 sm:grid-cols-3">
          {STEPS.map(([step, detail], index) => (
            <li key={step} className="flex gap-3">
              <span
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-full font-display text-sm font-medium",
                  index === 0
                    ? "bg-primary text-primary-foreground"
                    : "bg-accent text-primary",
                )}
              >
                {index + 1}
              </span>
              <span className="text-sm">
                <span className="font-medium">{step}</span>
                <span className="block text-muted-foreground">{detail}</span>
              </span>
            </li>
          ))}
        </ol>
        <NextStep report={report} />
      </section>

      <section aria-labelledby="postings" className="space-y-4">
        <h2 id="postings" className="font-display text-2xl font-medium">
          The postings
        </h2>
        {report.postings.length ? (
          <ul className="divide-y rounded-xl border bg-card shadow-sm">
            {report.postings.map((posting) => (
              <PostingCard
                key={posting.url}
                posting={posting}
                token={report.token}
              />
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground">
            There were no open postings for Ontario on the board.
          </p>
        )}
      </section>

      <section aria-labelledby="process" className="space-y-4">
        <div>
          <h2 id="process" className="font-display text-2xl font-medium">
            What a posting can't show
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Two rules are about how you hire, not what you post. Your answers
            stay with this report.
          </p>
        </div>
        <Checklist report={report} />
      </section>

      <footer className="space-y-2 border-t pt-6 text-xs text-muted-foreground">
        <p>
          A summary to help you review your postings, not legal advice. "May
          need" means the posting doesn't appear to meet the rule as we read it;
          you know your headcount and exemptions best.
        </p>
        {report.expires_on && (
          <p>
            This report is deleted on {formatDay(report.expires_on)} unless you
            save it to an account.
          </p>
        )}
      </footer>
    </div>
  )
}
