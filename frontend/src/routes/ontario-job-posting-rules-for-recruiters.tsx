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
import { Source } from "@/components/Site/rules/Source"
import { SOURCES } from "@/components/Site/rules/types"

// Statements match docs/law-review-2026-10.md (sections 2 and 6) and the rule pages. Whose headcount counts when
// an agency posts for a client is an open question there (Q9b), so the page says so instead of answering it.
const TITLE = "Ontario job posting rules for recruiters (2026)"
const DESCRIPTION =
  "What Ontario's 2026 job posting rules mean when you post for clients: who's responsible, AI screening tools, talent pools, and a client intake checklist."

export const Route = createFileRoute(
  "/ontario-job-posting-rules-for-recruiters",
)({
  component: Recruiters,
  head: guideHead("recruiters", TITLE, DESCRIPTION),
})

const { reg, guide } = SOURCES.en

const INTAKE = `Client intake for an Ontario job posting
[ ] Expected pay, or a pay range no wider than $50,000 a year (or confirmation that the pay is above $200,000 a year)
[ ] Is this an existing vacancy, or a pool for future openings?
[ ] Do you, or do we, use AI to screen, assess or select applicants for this job? Which tools?
[ ] How many employees does the employer have in Ontario today?
[ ] Is the job done in Ontario?
[ ] The application form's questions, to check them for Canadian experience requirements
[ ] Who tells interviewed applicants, within 45 days, whether a hiring decision has been made?
[ ] Who keeps the posting, its form and those updates for three years?`

const FAQ: Question[] = [
  {
    q: "Do Ontario's job posting rules apply to recruitment agencies?",
    a: 'They apply to the postings an agency advertises for an employer. The regulation defines a publicly advertised job posting as one that "an employer or a person acting on behalf of an employer advertises to the general public" (O. Reg. 476/24, s. 2 (1)), and the Ministry\'s guide says the employer is responsible for making sure the requirements are followed.',
  },
  {
    q: "Does my client's posting need an AI statement if only my agency uses AI?",
    a: "Yes, if your agency uses AI to screen, assess or select applicants for that job. The Ministry's guide says the rule applies equally when an employer engages a third party, such as a recruiting firm, to do that.",
  },
  {
    q: "Is an evergreen or talent pool posting covered?",
    a: "A general campaign that doesn't advertise a specific position isn't covered, such as an ad that only says \"we are always looking for talent\". A posting for a named job is, and if there's no existing vacancy it must say so.",
  },
]

function Recruiters() {
  return (
    <GuidePage
      id="recruiters"
      title={TITLE}
      description={DESCRIPTION}
      h1="Ontario's job posting rules for recruiters and staffing agencies"
      intro={
        <p>
          If you post jobs for clients, Ontario's job posting rules reach your
          work too: they cover a posting that an employer, or a person acting on
          behalf of an employer, advertises to the public. Here is what that
          means for an agency, and a checklist to send clients at intake.
        </p>
      }
      faq={FAQ}
    >
      <Part title="Who's responsible">
        <List>
          <li>
            A posting you advertise for a client is a publicly advertised job
            posting, the same as one the client publishes itself (
            <Source href={reg}>O. Reg. 476/24, s. 2 (1)</Source>).
          </li>
          <li>
            The Ministry's guide says that when a third party or a job board
            carries a posting, the employer is responsible for making sure the
            requirements are followed (
            <Source href={guide}>Ministry's guide</Source>).
          </li>
          <li>
            In practice, clients will expect what you publish for them to meet
            the rules. Agree who checks each posting before it goes up.
          </li>
        </List>
      </Part>

      <Part title="Whose size counts">
        <List>
          <li>
            The rules don't apply to an employer with fewer than 25 employees on
            the day the job is posted (
            <Source href={reg}>O. Reg. 476/24, s. 1</Source>).
          </li>
          <li>
            The Ministry's guide counts a temporary help agency's assignment
            employees toward the agency's total, not the client's (
            <Source href={guide}>Ministry's guide</Source>).
          </li>
          <li>
            When you recruit for a client's own job, whether the client's size
            is the one that decides is a point to confirm with an employment
            lawyer. CheckON looks up the employer named in the posting, and
            applies the rules when it can't find a size.
          </li>
        </List>
      </Part>

      <Part title="AI tools you use count for your client">
        <List>
          <li>
            An employer who uses artificial intelligence to screen, assess or
            select applicants must say so in the posting. The Ministry's guide
            says this applies equally when a third party, such as a recruiting
            firm, does the screening for the employer (ESA, s. 8.4 (1);{" "}
            <Source href={guide}>Ministry's guide</Source>).
          </li>
          <li>
            So if your ATS ranks candidates, or a tool scores resumes or runs a
            screening chat for a client's job, that client's posting needs the
            statement. Whether a particular tool counts depends on the facts,
            the guide says.
          </li>
        </List>
        <CopyBlock
          id="recruiters"
          item="ai-wording"
          title="Wording when a recruiter uses AI"
          label="Copy the AI wording"
          text="Our recruiting partner uses artificial intelligence to screen, assess or select applicants for this position."
        />
        <p>
          <PageLink to={RULES.ai.path}>More on AI disclosure</PageLink>
        </p>
      </Part>

      <Part title="Talent pools and evergreen postings">
        <List>
          <li>
            A general recruitment campaign that doesn't advertise a specific
            position isn't covered, such as an ad that only says "we are always
            looking for talent" (
            <Source href={reg}>O. Reg. 476/24, s. 2 (1) (a)</Source>;{" "}
            <Source href={guide}>Ministry's guide</Source>).
          </li>
          <li>
            A posting for a named job is for a specific position, even when
            you're building a pool for future openings. If there's no existing
            vacancy, the posting must say so (ESA, s. 8.5 (1) (a);{" "}
            <Source href={guide}>Ministry's guide</Source>), for example: "This
            posting is not for an existing vacancy. We're collecting
            applications for future openings."
          </li>
        </List>
        <p>
          <PageLink to={RULES.vacancy.path}>
            More on the vacancy statement
          </PageLink>
        </p>
      </Part>

      <Part title="Screening questions and application forms">
        <List>
          <li>
            The ban on Canadian experience requirements covers the posting "or
            any associated application form" (ESA, s. 8.3 (1)). Check the
            screening questions in your ATS, not only the ad.
          </li>
          <li>
            Professional licensing and registration requirements are allowed,
            the Ministry's guide says.
          </li>
        </List>
        <p>
          <PageLink to={RULES.cex.path}>More on Canadian experience</PageLink>
        </p>
      </Part>

      <Part title="After the interviews">
        <List>
          <li>
            Within 45 days of an applicant's interview, or of the last one, the
            employer must tell them whether a hiring decision has been made, and
            keep the posting, its form and that update for three years (ESA, ss.
            8.6 and 15; O. Reg. 476/24, s. 5).
          </li>
          <li>
            When you run the interviews for a client, agree who sends the update
            and who keeps the records.
          </li>
        </List>
        <p>
          <PageLink to={RULES.interview.path}>More on the 45-day rule</PageLink>
        </p>
      </Part>

      <Part title="A client intake checklist">
        <p>
          The facts a posting needs that only the client knows. Send it with
          each new job order.
        </p>
        <CopyBlock
          id="recruiters"
          item="intake"
          title="Client intake"
          label="Copy the intake checklist"
          text={INTAKE}
        />
      </Part>

      <GuideCta
        id="recruiters"
        title="Check every client's postings the same way"
        label="See the Agency plan"
        hash="pricing"
        cta="agency-plan"
        more={
          <GuideButton id="recruiters" to="/check" hash="check" cta="check">
            Check a posting free
          </GuideButton>
        }
      >
        <p>
          CheckON's Agency plan gives each client a workspace with its own
          company profile, so each check starts from that client's answers. You
          can audit a client's careers page, fix each posting with a check, and
          keep an archive of the postings you approved.
        </p>
      </GuideCta>
    </GuidePage>
  )
}
