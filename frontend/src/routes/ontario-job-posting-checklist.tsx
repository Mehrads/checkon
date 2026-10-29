import { createFileRoute, Link } from "@tanstack/react-router"
import { Printer } from "lucide-react"

import { CopyButton } from "@/components/Site/CopyButton"
import {
  GuideButton,
  GuideCta,
  GuidePage,
  guideHead,
  type Question,
} from "@/components/Site/Guide"
import { RULES } from "@/components/Site/rules/en"
import { Button } from "@/components/ui/button"
import { track } from "@/lib/analytics"

// Every item matches the rule pages (components/Site/rules/en.tsx), the rule pack and docs/law-review-2026-10.md;
// change it when they change. Content pages may name the rules and cite the sections.
const TITLE = "Ontario job posting checklist (2026)"
const DESCRIPTION =
  "A checklist for Ontario job postings since January 1, 2026: pay range, vacancy statement, AI disclosure, Canadian experience, 45-day reply and records."

export const Route = createFileRoute("/ontario-job-posting-checklist")({
  component: Checklist,
  head: guideHead("checklist", TITLE, DESCRIPTION),
})

interface Item {
  text: string
  cite: string
  more?: { to: string; label: string }
}

const GROUPS: { title: string; note?: string; items: Item[] }[] = [
  {
    title: "First: do the rules apply?",
    note: "If all four are true, the rest of the list applies to the posting.",
    items: [
      {
        text: "The employer has 25 or more employees in Ontario on the day the job is posted. Count people, not full-time equivalents: part-time and casual staff each count as one.",
        cite: "O. Reg. 476/24, s. 1; Ministry's guide",
      },
      {
        text: "The posting is advertised to the public, not only to current employees.",
        cite: "O. Reg. 476/24, s. 2 (1)",
      },
      {
        text: "It's for a specific job, not a general \"we're hiring\" campaign that names no position.",
        cite: "O. Reg. 476/24, s. 2 (1)",
      },
      {
        text: "The job is done in Ontario.",
        cite: "O. Reg. 476/24, s. 2 (1)",
      },
    ],
  },
  {
    title: "In the posting",
    items: [
      {
        text: "The expected pay, or a range of expected pay, is in the posting.",
        cite: "ESA, s. 8.2 (1)",
        more: { to: RULES.pay.path, label: "Pay ranges" },
      },
      {
        text: "A range is no wider than $50,000 a year. Hourly, weekly and monthly pay count by their yearly equivalent. If the pay, or the top of the range, is more than $200,000 a year, the pay rule doesn't apply.",
        cite: "ESA, s. 8.2 (2) and (3); O. Reg. 476/24, ss. 3 and 4",
      },
      {
        text: "Each part of the pay is described: base pay, commission, and bonuses tied to hours, production or efficiency.",
        cite: "Ministry's guide",
      },
      {
        text: 'A sentence says whether the posting is for an existing vacancy, for example "This posting is for an existing vacancy."',
        cite: "ESA, s. 8.5 (1) (a)",
        more: { to: RULES.vacancy.path, label: "The vacancy statement" },
      },
      {
        text: "If you, or a recruiter working for you, use AI to screen, assess or select applicants, the posting says so.",
        cite: "ESA, s. 8.4 (1); Ministry's guide",
        more: { to: RULES.ai.path, label: "AI disclosure" },
      },
      {
        text: "Nothing requires Canadian experience: not Canadian work experience, Canadian education credentials, or an established network or client base in Canada. Licensing and registration requirements are allowed.",
        cite: "ESA, s. 8.3 (1); Ministry's guide",
        more: { to: RULES.cex.path, label: "Canadian experience" },
      },
    ],
  },
  {
    title: "Around the posting",
    items: [
      {
        text: "The application form's questions don't ask for Canadian experience either.",
        cite: "ESA, s. 8.3 (1)",
      },
      {
        text: "Any document or web page the posting links to is checked too: it counts as part of the posting.",
        cite: "Ministry's guide",
      },
    ],
  },
  {
    title: "After you post",
    items: [
      {
        text: "Within 45 days of an interview, or of the last one, each interviewed applicant is told whether a hiring decision has been made.",
        cite: "ESA, s. 8.6; O. Reg. 476/24, s. 5",
        more: { to: RULES.interview.path, label: "The 45-day rule" },
      },
      {
        text: "A copy of each public version of the posting, and of its application form, is kept for three years after the posting comes down.",
        cite: "ESA, s. 15 (7.1)",
        more: { to: RULES.records.path, label: "Record keeping" },
      },
      {
        text: "What you told each interviewed applicant is kept for three years after you told them.",
        cite: "ESA, s. 15 (7.1.1)",
      },
    ],
  },
]

/** The list as plain text, to paste into a document or a task tool. */
const PLAIN = [
  "Ontario job posting checklist (checkon.ca/ontario-job-posting-checklist)",
  ...GROUPS.flatMap((group) => [
    "",
    group.title,
    ...group.items.map((item) => `[ ] ${item.text} (${item.cite})`),
  ]),
].join("\n")

const FAQ: Question[] = [
  {
    q: "What must an Ontario job posting include in 2026?",
    a: "For employers with 25 or more employees in Ontario: the expected pay or a pay range no wider than $50,000 a year (unless the pay is more than $200,000), a statement on whether the posting is for an existing vacancy, and, if AI is used to screen, assess or select applicants, a statement saying so. It can't include a Canadian experience requirement.",
  },
  {
    q: "Do the rules apply to small businesses?",
    a: "Not to employers with fewer than 25 employees on the day the job is posted (O. Reg. 476/24, s. 1). Count every employee in Ontario as one, including part-time and casual staff and people on leave.",
  },
  {
    q: "Do the rules cover internal postings?",
    a: "No. A posting restricted to the employer's existing employees isn't a publicly advertised job posting (O. Reg. 476/24, s. 2 (1)).",
  },
]

function Checklist() {
  const page = "checklist"
  return (
    <GuidePage
      id="checklist"
      title={TITLE}
      description={DESCRIPTION}
      h1="Ontario job posting checklist"
      intro={
        <p>
          Go through this before you publish a job in Ontario. It covers what
          the Employment Standards Act asks of a public job posting since
          January 1, 2026, and what to do after you post. Copy it into your own
          process, or print it.
        </p>
      }
      faq={FAQ}
    >
      <div className="flex flex-wrap gap-3 print:hidden">
        <CopyButton
          text={PLAIN}
          label="Copy the checklist"
          words={{ copy: "Copy the checklist", copied: "Copied" }}
          onCopied={() => track("content-copy", { page, item: "checklist" })}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            track("content-print", { page })
            window.print()
          }}
        >
          <Printer />
          Print
        </Button>
      </div>

      {GROUPS.map((group) => (
        <section key={group.title} className="space-y-3">
          <h2 className="font-display text-2xl font-medium tracking-[-0.01em]">
            {group.title}
          </h2>
          {group.note && <p className="text-muted-foreground">{group.note}</p>}
          <ul className="divide-y rounded-lg border bg-card">
            {group.items.map((item) => (
              <li key={item.text} className="flex gap-3 p-4">
                <span
                  className="mt-1 size-4 shrink-0 rounded-sm border border-primary/60"
                  aria-hidden="true"
                />
                <div className="min-w-0 space-y-1">
                  <p>{item.text}</p>
                  <p className="text-sm text-muted-foreground">
                    {item.cite}
                    {item.more && (
                      <>
                        {" · "}
                        <Link
                          to={item.more.to}
                          className="text-primary underline-offset-4 hover:underline print:hidden"
                        >
                          {item.more.label}
                        </Link>
                      </>
                    )}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}

      <GuideCta
        id="checklist"
        title="Let CheckON go through the posting part"
        more={
          <GuideButton id="checklist" to="/check" hash="sample" cta="sample">
            See a sample result
          </GuideButton>
        }
      >
        <p>
          Paste a posting and CheckON checks the "In the posting" items for you,
          and the application form when you add it. It quotes each line that
          needs work and suggests the smallest fix, which you approve. The first
          check each week is free, with no sign-up.
        </p>
      </GuideCta>
    </GuidePage>
  )
}
