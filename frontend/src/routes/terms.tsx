import { createFileRoute } from "@tanstack/react-router"

import {
  LegalPage,
  List,
  Operator,
  PageLink,
  Part,
} from "@/components/Site/Legal"
import { pageHead } from "@/lib/seo"

// Every statement here describes what the code does; change this page when that changes. Whoever runs a copy of
// CheckON adds their own terms: who they are, the law that applies and how they handle accounts.
const DRAFTED = "November 5, 2026"

export const Route = createFileRoute("/terms")({
  component: TermsPage,
  head: () =>
    pageHead({
      path: "/terms",
      title: "CheckON: Terms of use",
      description:
        "The terms for using CheckON: what a check does, accounts, your postings and fair use.",
    }),
})

function TermsPage() {
  return (
    <LegalPage
      eyebrow="Terms"
      title="Terms of use"
      drafted={DRAFTED}
      draftNote="These terms describe how the CheckON software works. They aren't reviewed by a lawyer, and whoever runs this site should complete them before relying on them."
    >
      <p className="text-muted-foreground">
        These terms apply when you use this site, including the free check,
        accounts and the browser extension. CheckON is open-source software
        under the Apache-2.0 licence; this site is run by its operator. By using
        it, you agree to these terms.
      </p>

      <Part title="The short version">
        <List>
          <li>
            CheckON checks postings against Ontario's job posting requirements.
            It isn't legal advice.
          </li>
          <li>
            Visitors get the free check. An account adds a check history,
            company profiles, client workspaces, pay suggestions, careers page
            audits and the archive.
          </li>
          <li>Nothing is billed.</li>
        </List>
      </Part>

      <Part title="The service">
        <p>
          CheckON reads a job posting you paste, link to or open in the browser
          extension, checks it against Ontario's job posting requirements, and
          suggests changes you can accept or reject. Some results depend on
          facts the posting doesn't state, such as how many employees an
          employer has. CheckON estimates these from a web search or asks you,
          and the result depends on that estimate and your answers.
        </p>
        <p>
          You decide what to publish. Read the result before you use it, and
          talk to an employment lawyer about your own situation.
        </p>
      </Part>

      <Part title="Checks and limits">
        <List>
          <li>
            The free check, for visitors who aren't signed in, has a weekly
            limit set by the site's operator, and pauses for the rest of the day
            once its daily spending cap is reached.
          </li>
          <li>
            The operator may also limit each account's checks in any 30 days.
            Your account page shows how many you've used.
          </li>
          <li>
            A check counts when CheckON shows you its results. Text that isn't
            one job posting, and checks that fail, don't count. Answering the
            check's questions and applying its fixes don't count again. Checking
            an application form uses one more check.
          </li>
        </List>
      </Part>

      <Part title="Your account">
        <List>
          <li>
            The operator decides who gets an account: by sign-up with your
            email, when it's open, or by adding you themselves. You set your
            password from a link that works for 48 hours. Signing in takes your
            password and a code emailed to you.
          </li>
          <li>
            Keep your password to yourself, and tell <Operator /> if you think
            someone else has used your account.
          </li>
          <li>You can delete your account anytime under Settings.</li>
        </List>
      </Part>

      <Part title="Your postings">
        <p>
          You keep all rights to the postings you check. You let this site
          process them only to run the check, show you the results and, if you
          turn it on, keep them in your archive. Only paste postings you're
          allowed to share. How they're handled, including what's kept, is on
          the <PageLink to="/privacy">privacy page</PageLink>.
        </p>
      </Part>

      <Part title="Fair use">
        <p>Don't use this site to:</p>
        <List>
          <li>break the law or post discriminatory or misleading job ads;</li>
          <li>
            get around the free check's limits or your account's, for example
            with many accounts or scripts;
          </li>
          <li>disrupt or overload the service, or break its security.</li>
        </List>
        <p>The operator may suspend an account that does.</p>
      </Part>

      <Part title="No guarantee">
        <p>
          CheckON is provided as it is, without warranty, as the Apache-2.0
          licence says. Its results may be wrong or incomplete, and the service
          may stop. As far as the law allows, neither the operator nor CheckON's
          authors are responsible for losses from using it.
        </p>
      </Part>

      <Part title="Questions and changes">
        <p>
          Questions about these terms go to <Operator />. When the terms change,
          this page and its date change too.
        </p>
      </Part>
    </LegalPage>
  )
}
