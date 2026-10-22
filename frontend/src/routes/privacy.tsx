import { createFileRoute } from "@tanstack/react-router"

import {
  Code,
  LegalPage,
  List,
  Mail,
  PageLink,
  Part,
} from "@/components/Site/Legal"

// Every statement here describes what the code does; change this page when that changes.
const DRAFTED = "October 22, 2026"

export const Route = createFileRoute("/privacy")({
  component: PrivacyPage,
  head: () => ({
    meta: [
      { title: "CheckON: Privacy policy" },
      {
        name: "description",
        content:
          "What CheckON collects when you check a job posting, why, who we share it with and how long we keep it.",
      },
    ],
  }),
})

function PrivacyPage() {
  return (
    <LegalPage
      eyebrow="Privacy"
      title="Privacy policy"
      drafted={DRAFTED}
      draftNote="This policy describes how CheckON handles information today. A lawyer hasn't reviewed it yet, so the wording may change."
    >
      <p className="text-muted-foreground">
        CheckON (checkon.ca) checks job postings for Ontario employers and the
        agencies that post for them. This page covers the website, the browser
        extension and the paid plans, and follows Canada's private-sector
        privacy law, PIPEDA.
      </p>

      <Part title="What we collect, and how long we keep it">
        <List>
          <li>
            <strong>Your posting.</strong> Sent to our AI provider to run the
            check and held in memory for up to an hour so you can apply fixes.
            We don't save it, unless you tick "Share this posting" when
            reporting a problem.
          </li>
          <li>
            <strong>Searches.</strong> We search the web for the employer's name
            and location to estimate its size (results kept 30 days), and, for
            pay suggestions, the job title and location (kept 7 days).
          </li>
          <li>
            <strong>Cookie and IP address.</strong> Used to enforce the weekly
            free check and stop abuse. We store only keyed hashes of them, not
            the values, and delete them after about 8 days.
          </li>
          <li>
            <strong>Usage records and feedback.</strong> What each check did,
            how long it took, plus any rating, comment or survey answer you
            give. Linked to a hashed cookie, never to your posting.
          </li>
          <li>
            <strong>Your account, if you subscribe.</strong> Email, name,
            password (hashed) and sign-in codes (expire after 10 minutes). Also
            your company profiles, client workspaces, confirmed pay ranges and
            check history (date, job title and result, never the posting). Kept
            until you delete your account.
          </li>
          <li>
            <strong>Billing.</strong> Stripe takes your card; we never see it.
            We keep your Stripe IDs, plan, status and billing dates, for as long
            as tax law requires (generally six years).
          </li>
          <li>
            <strong>Contact form.</strong> Your name, email, company and
            message, saved and emailed to <Mail /> so we can reply.
          </li>
          <li>
            <strong>Browser extension.</strong> Reads the posting on the current
            tab (your selection, the job field or the page text) only when you
            click the CheckON icon or "Check with CheckON", and writes text back
            only when you apply a fix. It doesn't track your browsing.
          </li>
          <li>
            <strong>Visits and logs.</strong> Umami counts page visits without
            cookies. Google Cloud keeps standard server logs, such as IP address
            and the page requested.
          </li>
        </List>
        <p>
          Usage records, feedback, shared postings and contact messages are kept
          while we need them to run and improve CheckON. Ask and we'll delete
          them sooner.
        </p>
      </Part>

      <Part title="Cookies and browser storage">
        <List>
          <li>
            <Code>free_check_id</Code>: a random ID for the weekly free check,
            kept for one year. Blocking it doesn't stop the checker.
          </li>
          <li>
            A sign-in token, in your browser or the extension, until you log out
            or it expires after 8 days.
          </li>
          <li>Your light or dark theme choice, never sent to us.</li>
        </List>
        <p>No advertising or cross-site tracking cookies.</p>
      </Part>

      <Part title="Who we share it with">
        <p>
          We don't sell personal information or share it for advertising. Our
          service providers are:
        </p>
        <List>
          <li>
            <strong>Anthropic</strong> (AI): postings and search terms.
          </li>
          <li>
            <strong>Google Cloud</strong> (hosting and database, Toronto
            region): everything we store.
          </li>
          <li>
            <strong>Google Workspace</strong> (email): contact messages.
          </li>
          <li>
            <strong>Stripe</strong> (payments): checkout details and extra-check
            counts.
          </li>
          <li>
            <strong>Umami Cloud</strong> (visit counts): page visits and a few
            actions.
          </li>
        </List>
        <p>
          Anthropic is in the United States, and other providers may process
          data outside Canada, where it's subject to local laws.
        </p>
      </Part>

      <Part title="How we protect it">
        <p>
          Connections are encrypted, data is stored encrypted in Canada, cookie
          IDs and IP addresses are hashed, and signing in takes your password
          plus an emailed code. Only CheckON's administrators can see feedback,
          contact messages and usage records.
        </p>
      </Part>

      <Part title="Your rights">
        <p>
          You can ask to see, correct or delete your information, or withdraw
          consent, by emailing <Mail />. We reply within 30 days. You can delete
          your account yourself under Settings once your plan is cancelled; see
          our <PageLink to="/terms">terms of service</PageLink>. If you're not
          satisfied, you can complain to the{" "}
          <a
            href="https://www.priv.gc.ca"
            className="text-primary underline-offset-4 hover:underline"
          >
            Office of the Privacy Commissioner of Canada
          </a>
          .
        </p>
      </Part>

      <Part title="Contact and changes">
        <p>
          CheckON is responsible for the personal information it handles.
          Questions go to <Mail />. When our practices change, we'll update this
          page and its date.
        </p>
      </Part>
    </LegalPage>
  )
}
