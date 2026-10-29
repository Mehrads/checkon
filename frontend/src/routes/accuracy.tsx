import { createFileRoute } from "@tanstack/react-router"
import { Check } from "lucide-react"

import {
  GuideButton,
  GuideCta,
  GuidePage,
  guideHead,
} from "@/components/Site/Guide"
import { List, Part } from "@/components/Site/Legal"
import { Source } from "@/components/Site/rules/Source"

// Every number is from docs/accuracy-and-demand-2026-10.md: sections 6 ("What the real postings show") and 7
// (after fixes 1–3, rule pack CA-ON@1.3.0). Measure again and update this page when the rule pack or the models
// change. No employer is named here.
const TITLE = "How accurate is CheckON? Tested on 150 real postings"
const DESCRIPTION =
  "We ran CheckON on 150 real Ontario job postings and compared each verdict with a separate reading of the law. Results by rule, the method and known limits."

export const Route = createFileRoute("/accuracy")({
  component: Accuracy,
  head: guideHead("accuracy", TITLE, DESCRIPTION),
})

const INDEED =
  "https://hiringlab.indeed.com/en-ca/2026/07/23/growth-in-canadian-salary-transparency-driven-by-two-provinces/"

/** Agreement with the separate reading on the 150 postings, and the same verdict in three runs (the 88 postings
 * with any flag), after the October fixes. */
const RESULTS = [
  ["Public posting for work in Ontario", "96%", "95%"],
  ["Expected pay shown", "95%", "98%"],
  ["Pay range no wider than $50,000", "97%", "99%"],
  ["Existing vacancy statement", "95%", "94%"],
  ["AI disclosure present", "99%", "99%"],
  ["No Canadian experience requirement", "96%", "94%"],
]

/** What the separate reading found in the 149 postings the rules applied to. */
const FOUND = [
  ["No plain statement on whether the job is an existing vacancy", "99", "66%"],
  ["No pay, and not exempt", "43", "29%"],
  ["A pay range wider than $50,000 a year", "5", "3%"],
  [
    "No AI statement (a gap only if the employer uses AI to screen, assess or select applicants)",
    "88",
    "59%",
  ],
  ["A Canadian experience requirement", "1", "under 1%"],
]

function Table({
  caption,
  head,
  rows,
}: {
  caption: string
  head: string[]
  rows: string[][]
}) {
  return (
    <div className="overflow-x-auto rounded-lg border bg-card">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b bg-muted/40">
          <tr>
            {head.map((cell, index) => (
              <th
                key={cell}
                scope="col"
                className={
                  index
                    ? "px-4 py-3 text-right font-medium"
                    : "px-4 py-3 font-medium"
                }
              >
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map(([first, ...rest]) => (
            <tr key={first}>
              <th scope="row" className="px-4 py-3 font-normal text-foreground">
                {first}
              </th>
              {rest.map((cell, index) => (
                <td
                  key={`${first}-${index}`}
                  className="px-4 py-3 text-right font-medium whitespace-nowrap text-foreground tabular-nums"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Accuracy() {
  return (
    <GuidePage
      id="accuracy"
      title={TITLE}
      description={DESCRIPTION}
      h1="How accurate is CheckON?"
      intro={
        <p>
          In October 2026 we ran CheckON on 150 real job postings from 48
          employers' public job boards and compared each verdict with a separate
          reading of the law. Here are the results, how we measured them, and
          where CheckON still gets it wrong.
        </p>
      }
      updated="Measured on October 27, 2026, with rule version CA-ON@1.3.0. Not legal advice."
    >
      <section
        aria-labelledby="in-short"
        className="rounded-xl border bg-paper p-5 sm:p-6"
      >
        <h2 id="in-short" className="text-sm font-medium text-primary">
          In short
        </h2>
        <ul className="mt-3 space-y-2">
          {[
            "CheckON's verdicts matched the separate reading 95% to 99% of the time, depending on the rule.",
            "None of the postings that the separate reading found non-compliant got a passing result (leaving out the AI rule, which depends on the employer's answer).",
            "In these tests it never made up a pay figure or any other fact. Missing pay gets a placeholder for you to fill in.",
            "Almost all the remaining disagreements on the vacancy statement and Canadian experience are points the law's text doesn't settle. We've listed them for an employment lawyer.",
          ].map((line) => (
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

      <Part title="Results by rule">
        <Table
          caption="CheckON's agreement with the separate reading, and its consistency, by rule"
          head={["What CheckON checks", "Agreed", "Same verdict in 3 runs"]}
          rows={RESULTS}
        />
        <p className="text-sm">
          Each rule was scored on the postings it applied to: 129 to 144 of the
          150. The percentages count every disagreement, including the points
          the law doesn't settle. "Same verdict in 3 runs" is measured on the 88
          postings with any finding, each checked three times.
        </p>
      </Part>

      <Part title="How we measured">
        <List>
          <li>
            <strong>The postings.</strong> 150 public postings for Ontario jobs
            from 48 employers, taken from their job boards on Lever (72),
            Greenhouse (60) and Ashby (18).
          </li>
          <li>
            <strong>The separate reading.</strong> AI reviewers labelled every
            posting from the text of the{" "}
            <Source href="https://www.ontario.ca/laws/statute/00e41">
              Employment Standards Act
            </Source>
            ,{" "}
            <Source href="https://www.ontario.ca/laws/regulation/240476">
              O. Reg. 476/24
            </Source>{" "}
            and the{" "}
            <Source href="https://www.ontario.ca/document/your-guide-employment-standards-act-0/requirements-related-publicly-advertised-job">
              Ministry's guide
            </Source>{" "}
            alone, without seeing CheckON's rules, prompts, code or results. We
            then read every disagreement against the law's text.
          </li>
          <li>
            <strong>What it isn't.</strong> These labels are our reading of the
            law, not a lawyer's. An employment lawyer hasn't reviewed them yet.
          </li>
          <li>
            <strong>Before and after.</strong> The first run found two weak
            spots: the vacancy statement (77% agreement) and Canadian experience
            (85%). We fixed both, ran the same postings again, and these are the
            results after the fixes.
          </li>
        </List>
      </Part>

      <Part title="What the 150 postings missed">
        <p>
          The separate reading also shows how often real postings miss a rule.
          The rules applied to 149 of them, mostly from established employers
          using modern applicant tracking systems.
        </p>
        <Table
          caption="What the separate reading found in the 149 postings the rules applied to"
          head={["Finding", "Postings", "Share"]}
          rows={FOUND}
        />
        <p>
          Leaving out AI, about 63% missed at least one rule. The most common
          gap, the vacancy statement, is usually one missing sentence. The share
          without pay matches what Indeed Hiring Lab reported for Ontario: 71%
          of postings showed pay in June 2026 (
          <Source href={INDEED}>Indeed Hiring Lab, July 23, 2026</Source>).
        </p>
      </Part>

      <Part title="What CheckON still gets wrong">
        <List>
          <li>
            It reads English postings. A few English postings that list French
            as a skill were refused as French: 2 to 5 of the 150, depending on
            the run.
          </li>
          <li>
            A range written as "CAD $95,000 to CAD $125,000" is read as two
            amounts, so CheckON asks which is right instead of reading the
            range.
          </li>
          <li>
            One AI notice written only for applicants in New York City was
            accepted as a disclosure.
          </li>
          <li>
            Some points need a lawyer's reading, such as whether "a replacement
            role" states an existing vacancy, or whether "Canadian or U.S.
            credentials are an asset" is a Canadian experience requirement.
            CheckON gives its reading; it isn't legal advice.
          </li>
          <li>
            It checks the text you give it. The employer's size comes from a web
            search, and when nothing is found CheckON assumes the rules apply.
          </li>
        </List>
      </Part>

      <GuideCta
        id="accuracy"
        title="Try it on your own posting"
        more={
          <GuideButton id="accuracy" to="/check" hash="sample" cta="sample">
            See a sample result
          </GuideButton>
        }
      >
        <p>
          Paste a posting and see each verdict with the line it's about and its
          source. The first check each week is free, with no sign-up.
        </p>
      </GuideCta>
    </GuidePage>
  )
}
