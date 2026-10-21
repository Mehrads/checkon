import { createFileRoute, Link } from "@tanstack/react-router"
import { FilePen } from "lucide-react"
import type { ReactNode } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Brand, SiteFooter } from "@/components/Site/Landing"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"

// Every statement here describes what the code does; change this page when that changes.
const EMAIL = "info@checkon.ca"
const DRAFTED = "October 21, 2026"

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

function Part({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      <div className="space-y-3 text-muted-foreground [&_strong]:font-medium [&_strong]:text-foreground">
        {children}
      </div>
    </section>
  )
}

function List({ children }: { children: ReactNode }) {
  return (
    <ul className="list-disc space-y-2 pl-5 marker:text-primary">{children}</ul>
  )
}

function Code({ children }: { children: ReactNode }) {
  return (
    <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em] text-foreground">
      {children}
    </code>
  )
}

const Mail = () => (
  <a
    href={`mailto:${EMAIL}`}
    className="text-primary underline-offset-4 hover:underline"
  >
    {EMAIL}
  </a>
)

function PrivacyPage() {
  return (
    <div className="min-h-svh bg-background">
      <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Brand href="/check" />
          <div className="flex items-center gap-2">
            <Appearance />
            <Button asChild size="sm">
              <Link to="/check">Check a posting</Link>
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-10 px-4 py-16 sm:px-6 sm:py-20">
        <div className="space-y-3">
          <p className="text-sm font-medium text-primary">Privacy</p>
          <h1 className="text-4xl font-semibold tracking-tight text-balance">
            Privacy policy
          </h1>
          <p className="text-muted-foreground">Draft of {DRAFTED}</p>
        </div>

        <Alert role="note" className="border-primary/40 bg-primary/5">
          <FilePen aria-hidden="true" />
          <AlertTitle>Draft for legal review</AlertTitle>
          <AlertDescription>
            This policy describes how CheckON handles information today. A
            lawyer hasn't reviewed it yet, so the wording may change.
          </AlertDescription>
        </Alert>

        <p className="text-muted-foreground">
          CheckON (checkon.ca) checks job postings for Ontario employers and the
          agencies that post for them. This page explains what information we
          collect, why we need it, who we share it with, how long we keep it and
          how to reach us about it. We wrote it with Canada's private-sector
          privacy law, PIPEDA, in mind.
        </p>

        <Part title="The short version">
          <List>
            <li>
              You don't need an account. The free check doesn't ask for your
              name or email.
            </li>
            <li>
              Your posting goes to our AI provider to run the check. We hold it
              for up to an hour and don't save it, unless you choose to share it
              with feedback.
            </li>
            <li>
              We set one cookie, to count your free weekly check. No advertising
              or tracking cookies.
            </li>
            <li>
              We store scrambled versions of that cookie and your IP address,
              not the values themselves.
            </li>
            <li>If you contact us, we keep your message so we can reply.</li>
          </List>
        </Part>

        <Part title="What we collect and why">
          <List>
            <li>
              <strong>The posting you paste.</strong> We need it to run the
              check. We send it to our AI provider, Anthropic, for analysis and
              keep it in our server's memory for up to an hour, so you can
              review the results, answer questions and apply fixes. It isn't
              saved to our database. Postings rarely contain personal
              information, but if yours names a person, such as a hiring
              contact, that name goes through the same steps.
            </li>
            <li>
              <strong>The employer's name.</strong> Some requirements depend on
              how many people an employer has. If the posting names the
              employer, we run a web search through our AI provider for that
              name, and the location if the posting gives one, to estimate the
              employer's size. We keep the result in memory for up to 30 days so
              we don't search for the same employer twice.
            </li>
            <li>
              <strong>A cookie for the free check.</strong> When you run a
              check, we set a cookie called <Code>free_check_id</Code>. It holds
              a random ID and nothing else, and lets us limit free checks per
              week.
            </li>
            <li>
              <strong>Your IP address.</strong> We use it to prevent abuse: to
              limit how many requests one address can send per minute, and as a
              second way to apply the weekly limit.
            </li>
            <li>
              <strong>Weekly-limit records.</strong> We don't store your cookie
              ID or IP address as they are. We store keyed hashes of them:
              one-way codes made with a secret key, which tell us whether we've
              seen the same value before but can't be turned back into it. We
              delete these records about 8 days after your check.
            </li>
            <li>
              <strong>Usage records.</strong> For each step of a check, we
              record what happened (for example, a check ran or was refused),
              how long it took and what it cost us to run. Each record carries a
              keyed hash of your cookie ID, so we can count returning visitors
              without knowing who they are. Usage records never contain your
              posting.
            </li>
            <li>
              <strong>Feedback.</strong> If you rate a finding or a fix, or
              report that a check looks wrong, we save your rating, the reason
              you pick and any comment, linked to that check. After a result we
              may ask one optional question about how you post jobs, such as
              which HR system you use. We save your answer the same way.
            </li>
            <li>
              <strong>Your posting, only if you choose.</strong> When you report
              a problem, you can tick "Share this posting with us so we can fix
              the mistake". Only then do we save the posting text with your
              feedback, so we can find and fix the mistake.
            </li>
            <li>
              <strong>The contact form.</strong> Your name, email, company
              (optional), what you're asking about and your message. We save it
              in our database and email it to <Mail />, our Google Workspace
              mailbox, so we can reply.
            </li>
            <li>
              <strong>Visit counts.</strong> On checkon.ca we use Umami Cloud to
              count visits and a few actions, such as running a check, copying a
              result or sending the contact form. Umami doesn't use cookies, and
              we don't send it your posting or anything you type into a form.
            </li>
            <li>
              <strong>Server logs.</strong> Our hosting provider, Google Cloud,
              keeps standard request logs, such as IP address, browser type and
              the page requested, to run and secure the service.
            </li>
          </List>
        </Part>

        <Part title="Cookies and browser storage">
          <List>
            <li>
              <Code>free_check_id</Code> is set when you run a check. It holds a
              random ID, lasts one year and can't be read by scripts on the
              page. We use it only for the weekly free-check limit.
            </li>
            <li>
              Your light or dark theme choice is saved in your browser and never
              sent to us.
            </li>
            <li>
              We don't use advertising, social media or cross-site tracking
              cookies.
            </li>
            <li>
              If you block or clear cookies, the checker still works. The weekly
              limit then relies on your IP address.
            </li>
          </List>
        </Part>

        <Part title="Who we share it with">
          <p>
            We don't sell personal information or share it for advertising. We
            use these service providers to run CheckON:
          </p>
          <List>
            <li>
              <strong>Anthropic</strong> (AI provider): the posting text, and
              the employer's name and location for the web search.
            </li>
            <li>
              <strong>Google Cloud</strong> (hosting and database): everything
              CheckON stores, in its Toronto region.
            </li>
            <li>
              <strong>Google Workspace</strong> (email): contact form messages
              and our replies.
            </li>
            <li>
              <strong>Umami Cloud</strong> (visit counts): page visits and the
              actions listed above.
            </li>
          </List>
          <p>
            Anthropic is based in the United States, and other providers may
            process information outside Canada. Information processed in another
            country is subject to that country's laws and may be accessible to
            its courts and authorities.
          </p>
        </Part>

        <Part title="How long we keep it">
          <List>
            <li>
              <strong>Your posting:</strong> up to an hour, in memory. Not saved
              unless you share it with feedback.
            </li>
            <li>
              <strong>Employer size searches:</strong> up to 30 days, in memory.
            </li>
            <li>
              <strong>Per-minute request counts by IP address:</strong> one
              minute, in memory.
            </li>
            <li>
              <strong>Weekly-limit records:</strong> about 8 days.
            </li>
            <li>
              <strong>
                The <Code>free_check_id</Code> cookie:
              </strong>{" "}
              one year in your browser, or until you clear it.
            </li>
            <li>
              <strong>
                Usage records, feedback, shared postings and contact messages:
              </strong>{" "}
              as long as we need them to run and improve CheckON and to reply to
              you. Ask and we'll delete them sooner.
            </li>
          </List>
        </Part>

        <Part title="How we protect it">
          <List>
            <li>Connections to checkon.ca are encrypted (HTTPS).</li>
            <li>
              The app and database run in Google Cloud's Toronto region, in
              Canada, which encrypts stored data.
            </li>
            <li>
              We store keyed hashes of cookie IDs and IP addresses instead of
              the values.
            </li>
            <li>
              Only CheckON's administrators can see saved feedback, contact
              messages and usage records.
            </li>
          </List>
        </Part>

        <Part title="Your choices and rights">
          <List>
            <li>
              You can use the free check without giving your name or email.
            </li>
            <li>
              Leave "Share this posting" unticked and we won't keep your
              posting.
            </li>
            <li>
              You can ask what personal information we hold about you, and ask
              us to correct or delete it. Email <Mail /> and we'll reply within
              30 days. Free-check records aren't linked to your name, so tell us
              roughly when you used CheckON to help us find them.
            </li>
            <li>
              You can withdraw consent, for example to a posting you shared, by
              emailing us.
            </li>
            <li>
              If you're not satisfied with our answer, you can complain to the{" "}
              <a
                href="https://www.priv.gc.ca"
                className="text-primary underline-offset-4 hover:underline"
              >
                Office of the Privacy Commissioner of Canada
              </a>
              .
            </li>
          </List>
        </Part>

        <Part title="Contact us">
          <p>
            CheckON is responsible for the personal information it handles. For
            questions about this policy, or to see, correct or delete your
            information, email <Mail />.
          </p>
        </Part>

        <Part title="Changes to this policy">
          <p>
            When the way we handle information changes, we'll update this page
            and the date at the top.
          </p>
        </Part>
      </main>
      <SiteFooter home="/check" />
    </div>
  )
}
