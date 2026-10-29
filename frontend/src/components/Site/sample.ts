import type { Patch, Verdict } from "@/client"

/** A real CheckON result for the public page's sample: the posting below, checked on the local stack on
 * 2026-10-28 (rule pack CA-ON@1.3.0, claude-haiku-5-5), both questions answered "yes", every fix approved and the
 * third pay option picked. Messages, quotes, questions and fixes are the API's own words; the citations are the
 * part of each rule's citation before its summary. The posting is made up and names no employer. Run it again and
 * update this file when the rule pack or the messages change. */
export const SAMPLE_CHECKED = "October 28, 2026"
export const SAMPLE_RULE_PACK = "CA-ON@1.3.0"

export const SAMPLE_TITLE = "Warehouse Shift Supervisor"
export const SAMPLE_LOCATION = "Mississauga, ON"

export const SAMPLE_POSTING = `Warehouse Shift Supervisor
Mississauga, ON · Full-time, on site

About the role
You'll lead a team of 12 on the evening shift at our distribution centre, keep orders moving and keep everyone safe.

What you'll do
• Plan the shift and assign the work
• Coach new team members
• Track productivity and safety numbers

What you bring
• 3+ years supervising in a warehouse, with Canadian experience required
• Forklift certification is an asset
• Clear communication in English

Pay and benefits
Salary: $55,000 to $110,000 a year, depending on experience.
Health and dental benefits from day one.

To apply, send your resume through our careers page.`

export interface SampleFinding {
  rule: string
  verdict: Verdict
  message: string
  citation: string
  /** The sentence the finding points at */
  quote?: string
  /** What CheckON asked, and the answer given */
  question?: string
  answer?: string
  /** The verdict once the question was answered */
  answered?: string
}

export const SAMPLE_FINDINGS: SampleFinding[] = [
  {
    rule: "ON-PAY-02",
    verdict: "fail",
    message: "The pay range is $55,000 a year wide; the limit is $50,000.",
    citation: "ESA 2000, s. 8.2 (3); O. Reg. 476/24, s. 4",
    quote: "$55,000 to $110,000 a year",
  },
  {
    rule: "ON-CEX-01",
    verdict: "fail",
    message:
      "The posting requires Canadian experience. Ask for the skill, not where it was gained.",
    citation: "ESA 2000, s. 8.3 (1)",
    quote:
      "3+ years supervising in a warehouse, with Canadian experience required",
  },
  {
    rule: "ON-VAC-01",
    verdict: "fail",
    message: "The posting doesn't say whether it is for an existing vacancy.",
    citation: "ESA 2000, s. 8.5 (1) (a)",
    question:
      "Is this posting for an existing vacancy, that is, a position that is imminently available for a qualified candidate to fill?",
    answer: "Yes",
  },
  {
    rule: "ON-AI-01",
    verdict: "needs_input",
    message:
      "Whether the posting needs an AI disclosure depends on your hiring tools.",
    citation: "ESA 2000, s. 8.4 (1)",
    question:
      "Do you, or a recruiter acting for you, use AI to screen, assess or select applicants for this job? This includes ATS auto-ranking, resume scoring and chat screening.",
    answer: "Yes",
    answered:
      "You use AI to screen, assess or select applicants, but the posting doesn't disclose it.",
  },
]

/** The rules the posting met as written */
export const SAMPLE_PASSED = ["ON-APPL-01", "ON-APPL-02", "ON-PAY-01"]

export interface SampleFix {
  rule: string
  writer: Patch["writer"]
  before?: string
  after: string
  /** The ranges offered, when the fix is a choice */
  options?: string[]
}

export const SAMPLE_FIXES: SampleFix[] = [
  {
    rule: "ON-PAY-02",
    writer: "code",
    before: "$55,000 to $110,000 a year",
    after: "$60,000 to $110,000 a year",
    options: [
      "$55,000 to $105,000 a year",
      "$57,000 to $107,000 a year",
      "$60,000 to $110,000 a year",
    ],
  },
  {
    rule: "ON-CEX-01",
    writer: "llm",
    before:
      "3+ years supervising in a warehouse, with Canadian experience required",
    after: "3+ years supervising in a warehouse",
  },
  {
    rule: "ON-VAC-01",
    writer: "wording_library",
    after: "This posting is for an existing vacancy.",
  },
  {
    rule: "ON-AI-01",
    writer: "wording_library",
    after:
      "We use artificial intelligence to screen, assess or select applicants for this position.",
  },
]

/** The posting with every fix approved: CheckON's verdict on it was "Meets the rules". */
export const SAMPLE_FINAL = `Warehouse Shift Supervisor
Mississauga, ON · Full-time, on site

About the role
You'll lead a team of 12 on the evening shift at our distribution centre, keep orders moving and keep everyone safe.

What you'll do
• Plan the shift and assign the work
• Coach new team members
• Track productivity and safety numbers

What you bring
• 3+ years supervising in a warehouse
• Forklift certification is an asset
• Clear communication in English

Pay and benefits
Salary: $60,000 to $110,000 a year, depending on experience.
Health and dental benefits from day one.

To apply, send your resume through our careers page.

This posting is for an existing vacancy.

We use artificial intelligence to screen, assess or select applicants for this position.`
