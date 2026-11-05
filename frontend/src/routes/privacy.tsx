import { createFileRoute } from "@tanstack/react-router"

import {
  Code,
  LegalPage,
  List,
  Operator,
  PageLink,
  Part,
} from "@/components/Site/Legal"
import { pageHead } from "@/lib/seo"

// Every statement here describes what the code does; change this page when that changes. Whoever runs a copy of
// CheckON adds what only they know: who they are, where it's hosted and which providers they use.
const DRAFTED = "November 5, 2026"

export const Route = createFileRoute("/privacy")({
  component: PrivacyPage,
  head: () =>
    pageHead({
      path: "/privacy",
      title: "CheckON: Privacy",
      description:
        "What CheckON collects when you check a job posting, why, who it's shared with and how long it's kept.",
    }),
})

function PrivacyPage() {
  return (
    <LegalPage
      eyebrow="Privacy"
      title="Privacy"
      drafted={DRAFTED}
      draftNote="This page describes what the CheckON software does with information. It isn't reviewed by a lawyer, and whoever runs this site should complete it before relying on it."
    >
      <p className="text-muted-foreground">
        CheckON checks job postings against Ontario's job posting rules. It's
        open-source software: this site is run by its operator, who is
        responsible for the information it handles. This page covers the
        website, accounts and the browser extension.
      </p>

      <Part title="What CheckON collects, and how long it's kept">
        <List>
          <li>
            <strong>Your posting and application form.</strong> Sent to the AI
            provider to run the check and held in memory for up to an hour so
            you can apply fixes. If you give a link, the server opens that page
            once to read the posting, and holds it the same way. A careers page
            audit, including the free sample, reads each posting from your
            public job board or careers page and handles it the same way. They
            aren't saved, unless you turn on the archive or tick "Share this
            posting" when reporting a problem.
          </li>
          <li>
            <strong>Searches.</strong> CheckON searches the web for the
            employer's name and location to estimate its size (results kept 30
            days), and, for pay suggestions, the job title and location (kept 7
            days).
          </li>
          <li>
            <strong>Cookie and IP address.</strong> Used to enforce the free
            check's limits and stop abuse. Only keyed hashes of them are stored,
            not the values, and they're deleted after about 8 days.
          </li>
          <li>
            <strong>Usage records and feedback.</strong> What each check did,
            how long it took, plus any rating, comment or survey answer you
            give. Linked to a hashed cookie, never to your posting.
          </li>
          <li>
            <strong>Your account, if you have one.</strong> Email, name,
            password (hashed) and sign-in codes (expire after 10 minutes), your
            check history (date, job title and result), company profiles, client
            workspaces, confirmed pay ranges and careers page audits (the page's
            address and each posting's title, place, link and result). Kept
            until the account is deleted.
          </li>
          <li>
            <strong>Archive, if you turn it on.</strong> You can turn on the
            archive for a company profile or client. Each posting you apply
            fixes to (or the edited version you save) is then kept, with its
            date and job title, and any application form text and documents you
            add. Each one is deleted 3 years after the takedown date you enter,
            and kept until you enter one. You can delete postings at any time,
            and deleting your account deletes its archive.
          </li>
          <li>
            <strong>Contact form.</strong> Your name, email, company and
            message, saved and emailed to the site's operator so they can reply.
          </li>
          <li>
            <strong>Browser extension.</strong> Reads the posting on the current
            tab (your selection, the job field or the page text) only when you
            click the CheckON icon or "Check with CheckON", and the application
            form's questions only when you click "Read form". It writes text
            back only when you apply a fix, and doesn't track your browsing.
          </li>
        </List>
      </Part>

      <Part title="Cookies and browser storage">
        <List>
          <li>
            <Code>free_check_id</Code>: a random ID for the free check, kept for
            one year. Blocking it doesn't stop the checker.
          </li>
          <li>
            A sign-in token, in your browser or the extension, until you log out
            or it expires after 8 days.
          </li>
          <li>Your light or dark theme choice, kept in your browser only.</li>
        </List>
        <p>No advertising or cross-site tracking cookies.</p>
      </Part>

      <Part title="Who it's shared with">
        <List>
          <li>
            <strong>The AI provider</strong> (Anthropic): postings, application
            forms and search terms, to run the check.
          </li>
          <li>
            <strong>The email provider</strong> the operator sets up: sign-in
            codes, password links and contact messages.
          </li>
          <li>
            <strong>Optional services</strong>, only if the operator turns them
            on: Umami counts page visits without cookies, and Langfuse records,
            for each check, which AI model ran, how long it took, what it cost
            and the result per rule, never your posting or anything that
            identifies you.
          </li>
        </List>
        <p>
          The operator also chooses where the site and its database are hosted.
          Ask them where your information is kept.
        </p>
      </Part>

      <Part title="How it's protected">
        <p>
          Cookie IDs and IP addresses are stored only as keyed hashes, passwords
          are hashed, and signing in takes your password plus an emailed code.
          Only the site's administrators can see feedback, contact messages and
          usage records.
        </p>
      </Part>

      <Part title="Your choices">
        <p>
          You can delete your account yourself under Settings, which deletes
          what it kept. To see, correct or delete other information, ask{" "}
          <Operator />. See also the{" "}
          <PageLink to="/terms">terms of use</PageLink>.
        </p>
      </Part>
    </LegalPage>
  )
}
