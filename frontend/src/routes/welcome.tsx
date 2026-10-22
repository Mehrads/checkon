import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { CircleCheck } from "lucide-react"
import { useEffect, useState } from "react"

import { BillingService } from "@/client"
import { AuthHeading, AuthLayout } from "@/components/Common/AuthLayout"
import { Button } from "@/components/ui/button"
import { isLoggedIn } from "@/hooks/useAuth"
import { track } from "@/lib/analytics"

export const Route = createFileRoute("/welcome")({
  component: Welcome,
  head: () => ({ meta: [{ title: "Welcome - CheckON" }] }),
})

// Stripe sends the webhook within seconds; stop asking after this long.
const WAIT_MS = 60_000

/** Where Stripe Checkout returns after payment. The account is made from the webhook, not from this page. */
function Welcome() {
  useEffect(() => track("checkout-done"), [])
  return (
    <AuthLayout>{isLoggedIn() ? <PlanStarting /> : <CheckEmail />}</AuthLayout>
  )
}

const NEXT = [
  ["Open our email", "It comes from CheckON, to the address you paid with."],
  ["Set your password", "The link in it works for 48 hours."],
  ["Log in", "With your password and a code we email you each time."],
]

function CheckEmail() {
  return (
    <div className="flex flex-col gap-6">
      <AuthHeading title="Thanks, you're subscribed">
        Three steps and you're checking postings on your plan.
      </AuthHeading>
      <ol className="space-y-4">
        {NEXT.map(([step, detail], index) => (
          <li key={step} className="flex gap-3">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-accent font-display text-sm font-medium text-primary">
              {index + 1}
            </span>
            <span className="text-sm">
              <span className="font-medium">{step}</span>
              <span className="block text-muted-foreground">{detail}</span>
            </span>
          </li>
        ))}
      </ol>
      <Button asChild>
        <Link to="/login">Log in</Link>
      </Button>
      <p className="border-t pt-5 text-xs text-muted-foreground">
        No email after a few minutes? Check your spam folder, or use "Forgot
        your password?" on the log-in page with the email you paid with.
      </p>
    </div>
  )
}

function PlanStarting() {
  const [since] = useState(Date.now)
  const { data } = useQuery({
    queryKey: ["billing"],
    queryFn: async () => (await BillingService.readBilling()).data,
    refetchInterval: (query) =>
      query.state.data?.plan || Date.now() - since > WAIT_MS ? false : 2000,
  })
  const ready = Boolean(data?.plan)
  return (
    <div className="flex flex-col gap-6">
      <CircleCheck className="size-9 text-primary" aria-hidden="true" />
      <AuthHeading
        title={
          ready
            ? `Your ${data?.plan_name} plan is active`
            : "Thanks for subscribing"
        }
      >
        {ready
          ? "Your checks are ready to use."
          : "We're setting up your plan. This usually takes a few seconds."}
      </AuthHeading>
      <Button asChild>
        <Link to="/">Start checking</Link>
      </Button>
    </div>
  )
}
