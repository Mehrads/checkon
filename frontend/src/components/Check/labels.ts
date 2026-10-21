import type { Patch, Status, Verdict } from "@/client"

export const RULE_NAMES: Record<string, string> = {
  "ON-APPL-01": "Employer size",
  "ON-APPL-02": "Public posting for work in Ontario",
  "ON-PAY-01": "Expected pay",
  "ON-PAY-02": "Pay range width",
  "ON-VAC-01": "Vacancy statement",
  "ON-AI-01": "AI disclosure",
  "ON-CEX-01": "Canadian experience",
}

export const STATUS_TEXT: Record<Status, string> = {
  compliant: "This posting meets Ontario's job posting rules.",
  not_compliant: "This posting doesn't meet Ontario's job posting rules yet.",
  needs_input: "Answer the questions below to finish the check.",
  not_applicable: "Ontario's job posting rules don't apply to this posting.",
}

/** The same statuses, said about the finished posting in the editor (nothing sits below it). */
export const FINAL_STATUS_TEXT: Record<Status, string> = {
  compliant: "Ready to publish: it meets Ontario's job posting rules.",
  not_compliant:
    "Some rules are still open. See the rule-by-rule results above.",
  needs_input:
    "Fill in what's marked in [brackets], and answer any open questions above, before you publish.",
  not_applicable: "Ontario's job posting rules don't apply to this posting.",
}

export const VERDICT_TEXT: Record<Verdict, string> = {
  pass: "Pass",
  fail: "Fail",
  warning: "Worth fixing",
  needs_input: "Needs an answer",
  not_applicable: "Doesn't apply",
}

export const VERDICT_CLASS: Record<Verdict, string> = {
  pass: "border-green-600 text-green-700 dark:text-green-400",
  fail: "border-transparent bg-destructive text-white",
  warning: "border-amber-500 text-amber-700 dark:text-amber-400",
  needs_input: "border-sky-500 text-sky-700 dark:text-sky-400",
  not_applicable: "text-muted-foreground",
}

export const WRITER_TEXT: Record<Patch["writer"], string> = {
  template: "Placeholder",
  code: "Calculated",
  wording_library: "Approved wording",
  llm: "Rewritten sentence",
}

export function ruleName(rule: string): string {
  return RULE_NAMES[rule] ?? rule
}
