import { createFileRoute } from "@tanstack/react-router"

import { LegalPage, List, Mail, PageLink, Part } from "@/components/Site/Legal"
import { pageHead } from "@/lib/seo"

// Every statement about plans and billing here describes what the code and the Stripe setup do
// (backend/app/api/billing.py, infra/README.md "Stripe"); change this page when they change.
const DRAFTED = "October 21, 2026"

export const Route = createFileRoute("/terms")({
  component: TermsPage,
  head: () =>
    pageHead({
      path: "/terms",
      title: "CheckON: Terms of service",
      description:
        "The terms for using CheckON, including paid plans: billing, renewal, cancellation and refunds.",
    }),
})

function TermsPage() {
  return (
    <LegalPage
      eyebrow="Terms"
      title="Terms of service"
      drafted={DRAFTED}
      draftNote="These terms describe how CheckON's plans work today. A lawyer hasn't reviewed them yet, so the wording may change before it's final."
    >
      <p className="text-muted-foreground">
        These terms apply when you use CheckON (checkon.ca), including the free
        check, the browser extension and the paid plans. By using CheckON, or by
        subscribing to a plan, you agree to them. If you subscribe for a
        business, you agree for that business and confirm you may do so.
      </p>

      <Part title="The short version">
        <List>
          <li>
            Starter and Agency are monthly subscriptions in Canadian dollars,
            paid by card through Stripe. They renew every month until you
            cancel.
          </li>
          <li>
            Each plan includes a number of checks per billing period. Extra
            checks cost $1 each and are billed on your next invoice.
          </li>
          <li>
            Cancel anytime under Manage billing. Your plan runs to the end of
            the period you've paid for, and we don't charge you again.
          </li>
          <li>We don't refund partial months, except as described below.</li>
          <li>
            CheckON checks postings against Ontario's job posting requirements.
            It isn't legal advice.
          </li>
        </List>
      </Part>

      <Part title="The service">
        <p>
          CheckON reads a job posting you paste or open in the browser
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

      <Part title="Plans and checks">
        <List>
          <li>
            <strong>Starter</strong> is $79 a month and includes 50 checks per
            billing period. <strong>Agency</strong> is $249 a month and includes
            300. Prices are in Canadian dollars. Sales taxes such as HST are
            added where they apply.
          </li>
          <li>
            A check counts when CheckON shows you its results. Text that isn't
            one job posting, and checks that fail on our side, don't count.
            Answering the check's questions and applying its fixes don't count
            again.
          </li>
          <li>Unused checks don't carry over to the next period.</li>
          <li>
            <strong>Extra checks.</strong> After your plan's checks are used,
            each further check in the same period costs $1. They're added to the
            invoice at the start of your next period. To protect you from a
            surprise bill, checks pause after 200 extra checks in a period until
            the next one starts. Email us if you need more.
          </li>
          <li>
            The checks belong to the business that subscribes and may only be
            used for its own postings, or, on Agency, for the clients it posts
            for.
          </li>
        </List>
      </Part>

      <Part title="Billing and renewal">
        <List>
          <li>
            Payments are handled by Stripe. We never see or store your card
            number.
          </li>
          <li>
            Your plan's monthly fee is charged at the start of each billing
            period, and the plan renews automatically every month until you
            cancel.
          </li>
          <li>
            Stripe emails your receipts. Your invoices are under Manage billing
            on your account page.
          </li>
          <li>
            If a payment fails, Stripe tries again over the following days and
            your checks keep working meanwhile. If the payment still doesn't go
            through, your plan ends and your account goes back to the free
            check.
          </li>
          <li>
            We may change a plan's price. We'll email you at least 30 days
            before, and the new price starts with your next period after that.
            If you don't want it, cancel before then.
          </li>
        </List>
      </Part>

      <Part title="Changing plans">
        <p>
          You can switch between Starter and Agency at any time on your account
          page. The switch happens straight away: we charge or credit the price
          difference for the rest of the current period, and the new plan's
          checks apply to the whole period.
        </p>
      </Part>

      <Part title="Cancelling">
        <List>
          <li>
            Cancel anytime under Manage billing on your account page. Your plan
            stays active until the end of the period you've paid for, then ends.
            We don't charge the monthly fee again.
          </li>
          <li>
            Extra checks you ran before the plan ends are billed on a final
            invoice.
          </li>
          <li>
            After your plan ends you can still sign in, see your past checks and
            use the free check. You can subscribe again at any time.
          </li>
        </List>
      </Part>

      <Part title="Refunds">
        <p>
          Monthly fees and extra checks aren't refundable once a period has
          started, and we don't refund partial months when you cancel or switch
          to a smaller plan. If we charged you by mistake, or a problem on our
          side kept you from using CheckON for a large part of a period, email{" "}
          <Mail /> within 30 days of the charge and we'll make it right with a
          refund or a credit. This doesn't limit any refund the law gives you.
        </p>
      </Part>

      <Part title="Your account">
        <List>
          <li>
            When you subscribe, we create an account with the email you give at
            checkout and email you a link to set a password. Signing in takes
            your password and a code we email you.
          </li>
          <li>
            Keep your password to yourself, and tell us at <Mail /> if you think
            someone else has used your account.
          </li>
          <li>
            To delete your account, cancel your plan first, then delete it under
            Settings.
          </li>
        </List>
      </Part>

      <Part title="Your postings">
        <p>
          You keep all rights to the postings you check. You let us process them
          only to run the check and show you the results. Only paste postings
          you're allowed to share with us. How we handle them, including what we
          keep, is in our <PageLink to="/privacy">privacy policy</PageLink>.
        </p>
      </Part>

      <Part title="Fair use">
        <p>Don't use CheckON to:</p>
        <List>
          <li>break the law or post discriminatory or misleading job ads;</li>
          <li>
            get around the free check's limits or your plan's checks, for
            example with many accounts or scripts;
          </li>
          <li>
            copy, resell or rebuild CheckON, its rules or its wording, or try to
            get them out of the service;
          </li>
          <li>disrupt or overload the service, or break its security.</li>
        </List>
        <p>
          We may suspend an account that does. Where we can, we'll tell you
          first and give you a chance to fix it.
        </p>
      </Part>

      <Part title="No guarantee, and our liability">
        <p>
          We work to keep CheckON accurate and available, but we can't promise
          that every result is correct or complete, or that the service never
          stops. CheckON is provided as it is. As far as the law allows, we
          aren't responsible for indirect losses, such as lost profits, and our
          total responsibility for any claim is limited to what you paid us in
          the 12 months before it.
        </p>
      </Part>

      <Part title="Changes to these terms">
        <p>
          When we change these terms, we'll update this page and the date at the
          top. For a change that affects paying customers, we'll email you at
          least 30 days before it applies.
        </p>
      </Part>

      <Part title="Law and contact">
        <p>
          These terms are governed by the laws of Ontario and the federal laws
          of Canada that apply there. Questions about them, or about a charge:{" "}
          <Mail />.
        </p>
      </Part>
    </LegalPage>
  )
}
