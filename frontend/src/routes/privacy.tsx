import { createFileRoute } from "@tanstack/react-router"

import {
  Code,
  LegalPage,
  List,
  Mail,
  PageLink,
  Part,
} from "@/components/Site/Legal"
import { pageHead } from "@/lib/seo"

// Every statement here describes what the code does; change this page when that changes.
const DRAFTED = "October 27, 2026"

export const Route = createFileRoute("/privacy")({
  component: PrivacyPage,
  head: () =>
    pageHead({
      path: "/privacy",
      title: "CheckON: Privacy policy",
      description:
        "What CheckON collects when you check a job posting, why, who we share it with and how long we keep it.",
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
        extension, free accounts, the paid plans and the reports we send
        employers about their public job postings. It follows Canada's
        private-sector privacy law, PIPEDA.
      </p>

      <Part title="What we collect, and how long we keep it">
        <List>
          <li>
            <strong>Your posting and application form.</strong> Sent to our AI
            provider to run the check and held in memory for up to an hour so
            you can apply fixes. If you give a link, our server opens that page
            once to read the posting, and holds it the same way. A careers page
            audit, including the free sample, reads each posting from your
            public job board or careers page and handles it the same way. We
            don't save them, unless you turn on the archive or tick "Share this
            posting" when reporting a problem.
          </li>
          <li>
            <strong>Searches.</strong> We search the web for the employer's name
            and location to estimate its size (results kept 30 days), and, for
            pay suggestions, the job title and location (kept 7 days).
          </li>
          <li>
            <strong>Cookie and IP address.</strong> Used to enforce the weekly
            free check and free sample audit, and stop abuse. We store only
            keyed hashes of them, not the values, and delete them after about 8
            days.
          </li>
          <li>
            <strong>Usage records and feedback.</strong> What each check did,
            how long it took, plus any rating, comment or survey answer you
            give. Linked to a hashed cookie, never to your posting.
          </li>
          <li>
            <strong>Your account, if you sign up or subscribe.</strong> Email,
            name, password (hashed) and sign-in codes (expire after 10 minutes),
            your check history (date, job title and result) and any reports you
            save to it. On a paid plan, also your company profiles, client
            workspaces, confirmed pay ranges and careers page audits (the page's
            address and each posting's title, place, link and result). Kept
            until you delete your account. A free account is then deleted
            entirely; a paid account's billing records stay, as described under
            Billing.
          </li>
          <li>
            <strong>Reports we send employers.</strong> We may check the open
            Ontario postings on an employer's public job board, and their
            application forms where the board shows them, and save the result on
            checkon.ca as a report: the company's name, the board's address,
            each posting's title, place, link and result, and short quotes from
            the postings. It opens from a private link in our email, without
            signing in. We count how many times it's opened and note when it was
            first opened, but not who opened it, and keep any answers given on
            it. A report nobody saves to an account is deleted 90 days after we
            make it; a saved one is kept until that account is deleted.
          </li>
          <li>
            <strong>Archive, if you turn it on.</strong> On a paid plan, you can
            turn on the archive for a company profile or client. We then save
            each posting you apply fixes to (or the edited version you save),
            with its date and job title, and any application form text and
            documents you add. Each one is deleted 3 years after the takedown
            date you enter, and kept until you enter one. You can delete
            postings at any time, and deleting a workspace or your account
            deletes its archive. If you cancel, you can still view and download
            it.
          </li>
          <li>
            <strong>Billing.</strong> Stripe takes your card; we never see it.
            We keep your Stripe IDs, plan, status, billing dates and the checks
            counted against your plan, for as long as tax law requires
            (generally six years).
          </li>
          <li>
            <strong>Contact form.</strong> Your name, email, company and
            message, saved and emailed to <Mail /> so we can reply.
          </li>
          <li>
            <strong>Browser extension.</strong> Reads the posting on the current
            tab (your selection, the job field or the page text) only when you
            click the CheckON icon or "Check with CheckON", and the application
            form's questions only when you click "Read form". It writes text
            back only when you apply a fix, and doesn't track your browsing.
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

      <Part title="Emails to employers">
        <p>
          We sometimes email a business about its public job postings, with a
          report as described above. We use only an email address the business
          publishes, such as a careers or hiring address, and the name and job
          title of the person who handles hiring when those are published. We
          keep those details, where we found them and what we sent, so we never
          email the same business twice. They stay on our own systems, never on
          the website or in the report.
        </p>
        <p>
          Every email says who we are and how to stop. Reply "no thanks", or
          email <Mail />, and we won't contact you again. Ask, and we'll delete
          what we kept about you, except a note not to contact you.
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
            <strong>Anthropic</strong> (AI): postings and search terms, and the
            public web pages we read when preparing an email to an employer.
          </li>
          <li>
            <strong>Google Cloud</strong> (hosting and database, Toronto
            region): everything we store.
          </li>
          <li>
            <strong>Google Workspace</strong> (email): contact messages, and the
            emails we send employers.
          </li>
          <li>
            <strong>Resend</strong> (email delivery): the emails we send, such
            as sign-in codes and password-reset links to your address, and
            contact-form messages to our inbox.
          </li>
          <li>
            <strong>Stripe</strong> (payments): checkout details and extra-check
            counts.
          </li>
          <li>
            <strong>Umami Cloud</strong> (visit counts): page visits and a few
            actions.
          </li>
          <li>
            <strong>Langfuse</strong> (monitoring): for each check, which AI
            model ran, how long it took, what it cost and the result per rule.
            Never your posting, the AI's answers or anything that identifies
            you.
          </li>
        </List>
        <p>
          Anthropic, Langfuse and Resend are in the United States, and other
          providers may process data outside Canada, where it's subject to local
          laws.
        </p>
      </Part>

      <Part title="How we protect it">
        <p>
          Connections are encrypted, data is stored encrypted in Canada, cookie
          IDs and IP addresses are hashed, and signing in takes your password
          plus an emailed code. A report's link is a long random address that
          can't be guessed, but anyone it's forwarded to can open it. Only
          CheckON's administrators can see feedback, contact messages and usage
          records.
        </p>
      </Part>

      <Part title="Your rights">
        <p>
          You can ask to see, correct or delete your information, or withdraw
          consent, by emailing <Mail />. We reply within 30 days. You can delete
          your account yourself under Settings: a free account anytime, a paid
          one once its plan is cancelled. To have a report deleted, email us;
          see our <PageLink to="/terms">terms of service</PageLink>. If you're
          not satisfied, you can complain to the{" "}
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
