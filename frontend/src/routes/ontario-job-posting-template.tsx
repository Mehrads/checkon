import { createFileRoute } from "@tanstack/react-router"

import {
  CopyBlock,
  GuideButton,
  GuideCta,
  GuidePage,
  guideHead,
  type Question,
} from "@/components/Site/Guide"
import { List, PageLink, Part } from "@/components/Site/Legal"
import { RULES } from "@/components/Site/rules/en"
import { SAMPLE_CHECKED, SAMPLE_FINAL } from "@/components/Site/sample"

// The inserted lines are the wording library's (backend/rulepacks/CA-ON/wording.yaml) and the rule pages'; change
// them together. Content pages may name the rules and cite the sections.
const TITLE = "Ontario job posting template (2026), free to copy"
const DESCRIPTION =
  "A free Ontario job posting template with the expected pay, vacancy statement and AI disclosure lines already in place. Copy it, fill it in, then check it."

export const Route = createFileRoute("/ontario-job-posting-template")({
  component: Template,
  head: guideHead("template", TITLE, DESCRIPTION),
})

const TEMPLATE = `[Job title]
[City], ON · [Full-time or part-time] · [On site, hybrid or remote]

About the role
[Two or three sentences: what the job is for and who it works with.]

What you'll do
• [Main duty]
• [Main duty]
• [Main duty]

What you bring
• [Number] years of experience in [skill or field]
• [Education, or equivalent experience]
• [A licence or registration, if the job legally needs one]

Pay and benefits
Expected pay: $[lowest] to $[highest] a year.
[Benefits]

This posting is [for / not for] an existing vacancy.

[Keep this line only if you, or a recruiter for you, use AI to screen, assess or select applicants:]
We use artificial intelligence to screen, assess or select applicants for this position.

How to apply
[How to apply, and the closing date if there is one.]`

const FAQ: Question[] = [
  {
    q: 'Can I write "competitive salary" instead of a range?',
    a: 'Not on its own. Since January 1, 2026, a public posting must include the expected pay or a range of expected pay (ESA, s. 8.2 (1)). You can still add "based on experience" after the range.',
  },
  {
    q: "Do I need the AI sentence?",
    a: "Only if you, or someone hiring for you such as a recruiter, use artificial intelligence to screen, assess or select applicants for the job (ESA, s. 8.4 (1)). The Ministry's guide says whether a tool counts depends on the facts of each case.",
  },
  {
    q: "What if the job isn't open yet?",
    a: "Say so. For a talent pool or future openings, write \"This posting is not for an existing vacancy.\" The Ministry's guide says that if the posting isn't for an existing vacancy, the employer must state that there is no existing vacancy.",
  },
]

function Template() {
  return (
    <GuidePage
      id="template"
      title={TITLE}
      description={DESCRIPTION}
      h1="A job posting template for Ontario"
      intro={
        <p>
          A plain template with the lines Ontario's job posting rules ask for
          already in place. Fill in the brackets, delete what doesn't apply, and
          check the result before you publish.
        </p>
      }
      faq={FAQ}
    >
      <CopyBlock
        id="template"
        item="template"
        title="The template"
        label="Copy the template"
        text={TEMPLATE}
      />

      <Part title="Why each line is there">
        <List>
          <li>
            <strong>Expected pay.</strong> A public posting must show the
            expected pay or a range, and a range can be at most $50,000 a year
            wide. For an hourly job, write it as "Pay: $24.50 to $28.00 an
            hour." <PageLink to={RULES.pay.path}>Pay ranges</PageLink>
          </li>
          <li>
            <strong>The vacancy line.</strong> Use "This posting is for an
            existing vacancy." when the job is open now, and "This posting is
            not for an existing vacancy." for a talent pool or future openings.{" "}
            <PageLink to={RULES.vacancy.path}>The vacancy statement</PageLink>
          </li>
          <li>
            <strong>The AI line.</strong> Only if AI is used to screen, assess
            or select applicants, by you or a recruiter working for you. It uses
            the law's own words; the Ministry's guide says it's enough to state
            that artificial intelligence is used to screen, assess or select
            applicants. <PageLink to={RULES.ai.path}>AI disclosure</PageLink>
          </li>
          <li>
            <strong>What you bring.</strong> Ask for the skill and the years,
            not where they were gained: no Canadian work experience, Canadian
            credentials or Canadian network. A licence or registration the job
            needs is allowed.{" "}
            <PageLink to={RULES.cex.path}>Canadian experience</PageLink>
          </li>
          <li>
            <strong>After you publish.</strong> Keep a copy of each version that
            goes public, and the application form, for three years after the
            posting comes down.{" "}
            <PageLink to={RULES.records.path}>Record keeping</PageLink>
          </li>
        </List>
      </Part>

      <Part title="A filled-in example">
        <p>
          The sample posting from our home page, after CheckON's suggested fixes
          were approved. CheckON's check on {SAMPLE_CHECKED} found that it meets
          the rules.
        </p>
        <CopyBlock
          id="template"
          item="example"
          title="Warehouse Shift Supervisor (made up)"
          label="Copy the example"
          text={SAMPLE_FINAL}
        />
      </Part>

      <GuideCta
        id="template"
        title="Filled it in? Check it before you publish"
        more={
          <GuideButton
            id="template"
            to="/ontario-job-posting-checklist"
            cta="checklist"
          >
            Open the checklist
          </GuideButton>
        }
      >
        <p>
          Paste your posting and CheckON quotes each line that needs work, shows
          the source and suggests the smallest fix, which you approve. The first
          check each week is free, with no sign-up.
        </p>
      </GuideCta>
    </GuidePage>
  )
}
