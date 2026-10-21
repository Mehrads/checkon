import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { CircleCheck, MailCheck } from "lucide-react"
import { useEffect, useState } from "react"

import { BillingService } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
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

function CheckEmail() {
  return (
    <div className="flex flex-col gap-4 text-center">
      <MailCheck className="mx-auto size-10 text-primary" aria-hidden="true" />
      <h1 className="text-2xl font-bold">Thanks, you're subscribed</h1>
      <p className="text-sm text-muted-foreground">
        We've emailed you a link to set your password. Set it, then log in with
        the email you paid with. We'll email you a sign-in code each time.
      </p>
      <Button asChild>
        <Link to="/login">Log in</Link>
      </Button>
      <p className="text-xs text-muted-foreground">
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
    <div className="flex flex-col gap-4 text-center">
      <CircleCheck
        className="mx-auto size-10 text-primary"
        aria-hidden="true"
      />
      <h1 className="text-2xl font-bold">
        {ready
          ? `Your ${data?.plan_name} plan is active`
          : "Thanks for subscribing"}
      </h1>
      <p className="text-sm text-muted-foreground">
        {ready
          ? "Your checks are ready to use."
          : "We're setting up your plan. This usually takes a few seconds."}
      </p>
      <Button asChild>
        <Link to="/">Start checking</Link>
      </Button>
    </div>
  )
}
