import { useMutation, useQueryClient } from "@tanstack/react-query"
import { CreditCard } from "lucide-react"
import { useState } from "react"

import { type BillingOut, BillingService } from "@/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  apiMessage,
  type PlanId,
  useCheckout,
  usePortal,
} from "@/hooks/useBilling"
import useCustomToast from "@/hooks/useCustomToast"
import { formatDay, PLAN_PRICE, UsageMeter } from "./UsageMeter"

const OTHER: Record<PlanId, { id: PlanId; name: string; checks: string }> = {
  starter: { id: "agency", name: "Agency", checks: "300" },
  agency: { id: "starter", name: "Starter", checks: "50" },
}

function SwitchPlan({ billing }: { billing: BillingOut }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const target = OTHER[billing.plan as PlanId]
  const change = useMutation({
    mutationFn: async () =>
      (await BillingService.changePlan({ body: { plan: target.id } })).data,
    onSuccess: (data) => {
      queryClient.setQueryData(["billing"], data)
      setOpen(false)
      showSuccessToast(`You're now on ${target.name}.`)
    },
    onError: (error) =>
      showErrorToast(apiMessage(error, "We couldn't change your plan.")),
  })
  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>
        Switch to {target.name}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Switch to {target.name}?</DialogTitle>
            <DialogDescription>
              {target.name} is {PLAN_PRICE[target.id]} a month with{" "}
              {target.checks} checks. The change starts now: we charge or credit
              the difference for the rest of this period on your card, and{" "}
              {target.name}'s checks apply to this whole period.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <LoadingButton
              loading={change.isPending}
              onClick={() => change.mutate()}
            >
              Switch to {target.name}
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

/** The plan, this period's checks, and the way to Stripe's portal. */
export function PlanCard({ billing }: { billing: BillingOut }) {
  const { showErrorToast } = useCustomToast()
  const portal = usePortal((error) =>
    showErrorToast(apiMessage(error, "We couldn't open billing.")),
  )
  const pastDue = billing.status === "past_due"
  return (
    <section className="space-y-4 rounded-xl border bg-card p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">Your plan</p>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold">{billing.plan_name}</h2>
            {pastDue ? (
              <Badge variant="destructive">Payment failed</Badge>
            ) : billing.cancel_at_period_end && billing.period_end ? (
              <Badge variant="outline">
                Ends {formatDay(billing.period_end)}
              </Badge>
            ) : (
              <Badge variant="outline">Active</Badge>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {billing.plan && !billing.cancel_at_period_end && (
            <SwitchPlan billing={billing} />
          )}
          <LoadingButton
            variant="outline"
            loading={portal.isPending}
            onClick={() => portal.mutate()}
          >
            <CreditCard />
            Manage billing
          </LoadingButton>
        </div>
      </div>
      {pastDue && (
        <Alert variant="destructive">
          <AlertTitle>Your last payment didn't go through</AlertTitle>
          <AlertDescription>
            Update your card under Manage billing to keep your plan. Checks keep
            working while Stripe retries the payment.
          </AlertDescription>
        </Alert>
      )}
      <UsageMeter billing={billing} />
    </section>
  )
}

/** For a signed-in user without an active plan: buy one. */
export function NoPlanCard({ billing }: { billing: BillingOut }) {
  const { showErrorToast } = useCustomToast()
  const checkout = useCheckout((_, error) =>
    showErrorToast(apiMessage(error, "We couldn't open the payment page.")),
  )
  const portal = usePortal((error) =>
    showErrorToast(apiMessage(error, "We couldn't open billing.")),
  )
  const ended = billing.status === "canceled" || billing.status === "unpaid"
  return (
    <section className="space-y-4 rounded-xl border bg-card p-5 shadow-sm sm:p-6">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">
          {ended ? "Your plan has ended" : "No plan yet"}
        </h2>
        <p className="text-sm text-muted-foreground">
          Without a plan you get the free check: one a week. Starter has 50
          checks a month, Agency 300, and extra checks are $1 each. Prices in
          Canadian dollars, billed monthly.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {billing.checkout_enabled ? (
          <>
            <LoadingButton
              loading={checkout.isPending && checkout.variables === "starter"}
              disabled={checkout.isPending}
              onClick={() => checkout.mutate("starter")}
            >
              Starter, {PLAN_PRICE.starter}/month
            </LoadingButton>
            <LoadingButton
              variant="outline"
              loading={checkout.isPending && checkout.variables === "agency"}
              disabled={checkout.isPending}
              onClick={() => checkout.mutate("agency")}
            >
              Agency, {PLAN_PRICE.agency}/month
            </LoadingButton>
          </>
        ) : (
          <Button asChild variant="outline">
            <a href="/check#contact">Contact us about a plan</a>
          </Button>
        )}
        {billing.has_billing && (
          <LoadingButton
            variant="ghost"
            loading={portal.isPending}
            onClick={() => portal.mutate()}
          >
            <CreditCard />
            Past invoices
          </LoadingButton>
        )}
      </div>
    </section>
  )
}
