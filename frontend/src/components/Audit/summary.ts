import type { AuditPostingPublic, AuditPublic } from "@/client"
import { formatDay } from "@/lib/utils"

export const SOURCE_NAME: Record<AuditPublic["source"], string> = {
  greenhouse: "Greenhouse",
  lever: "Lever",
  ashby: "Ashby",
  smartrecruiters: "SmartRecruiters",
  page: "Careers page",
}

/** What each rule is about, as a short phrase for the summary line ("Most common: expected pay"). */
const ISSUE_PHRASE: Record<string, string> = {
  "ON-APPL-01": "employer size",
  "ON-APPL-02": "whether the rules apply",
  "ON-PAY-01": "expected pay",
  "ON-PAY-02": "pay range width",
  "ON-VAC-01": "vacancy statement",
  "ON-AI-01": "AI disclosure",
  "ON-CEX-01": "Canadian experience",
}

export function issuePhrase(rule: string): string {
  return ISSUE_PHRASE[rule] ?? rule
}

/** The page's address without the scheme, for display. */
export function shortAddress(url: string): string {
  return url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "")
}

type Group =
  | "compliant"
  | "changes"
  | "answers"
  | "not_applicable"
  | "unchecked"
  | "pending"

export function group(posting: AuditPostingPublic): Group {
  switch (posting.status) {
    case "compliant":
      return "compliant"
    case "not_compliant":
      return "changes"
    case "needs_input":
      return "answers"
    case "not_applicable":
      return "not_applicable"
    case "refused":
    case "failed":
      return "unchecked"
    default:
      return "pending"
  }
}

function count(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`
}

function list(parts: string[]): string {
  if (parts.length < 2) return parts.join("")
  return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`
}

/** One line an agency can paste to its client: what was checked, the results, and the most common issues. No
 * legal citations: the client reads the full report for those. */
export function summaryLine(audit: AuditPublic): string {
  const by = (g: Group) => audit.postings.filter((p) => group(p) === g).length
  const done = audit.postings.length - by("pending")
  const parts = [
    by("compliant") &&
      `${by("compliant")} ${by("compliant") === 1 ? "meets" : "meet"} the rules`,
    by("changes") &&
      `${by("changes")} ${by("changes") === 1 ? "needs" : "need"} changes`,
    by("answers") &&
      `${by("answers")} ${by("answers") === 1 ? "needs" : "need"} answers from you before we can tell`,
    by("not_applicable") &&
      `${by("not_applicable")} ${by("not_applicable") === 1 ? "isn't" : "aren't"} covered by the rules`,
    by("unchecked") && `${by("unchecked")} couldn't be checked`,
  ].filter((part): part is string => Boolean(part))
  const issues = new Map<string, number>()
  for (const posting of audit.postings) {
    for (const issue of posting.issues) {
      if (issue.verdict !== "needs_input")
        issues.set(issue.rule, (issues.get(issue.rule) ?? 0) + 1)
    }
  }
  const common = [...issues.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(
      ([rule, n]) =>
        `${issuePhrase(rule)} (${count(n, "posting", "postings")})`,
    )
  const scope =
    done < audit.postings.length
      ? `${done} of ${audit.postings.length}`
      : `${audit.postings.length}`
  const checked = `On ${formatDay(audit.created_at)}, we checked ${scope} open Ontario job ${
    audit.postings.length === 1 ? "posting" : "postings"
  } on your careers page (${shortAddress(audit.url)}) against Ontario's job posting rules`
  return [
    `${checked}${parts.length ? `: ${list(parts)}.` : "."}`,
    common.length ? ` Most common issues: ${list(common)}.` : "",
  ].join("")
}
