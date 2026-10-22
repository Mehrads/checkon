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

const TILES: { id: PlanId; name: string; checks: number }[] = [
  { id: "starter", name: "Starter", checks: 50 },
  { id: "agency", name: "Agency", checks: 300 },
]

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
      queryClient.invalidateQueries({ queryKey: ["workspaces"] }) // Agency adds client workspaces
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
  const price = billing.plan ? PLAN_PRICE[billing.plan] : null
  return (
    <section className="overflow-hidden rounded-xl border bg-card shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 p-5 sm:p-6">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">Your plan</p>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="font-display text-3xl leading-tight font-medium tracking-[-0.01em]">
              {billing.plan_name}
            </h2>
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
          <p className="text-sm text-muted-foreground">
            {price}/month · {billing.checks_included} checks a month · extra
            checks $1 each
          </p>
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
        <div className="px-5 pb-5 sm:px-6">
          <Alert variant="destructive">
            <AlertTitle>Your last payment didn't go through</AlertTitle>
            <AlertDescription>
              Update your card under Manage billing to keep your plan. Checks
              keep working while Stripe retries the payment.
            </AlertDescription>
          </Alert>
        </div>
      )}
      <UsageMeter
        billing={billing}
        size="lg"
        className="border-t bg-muted/50 p-5 sm:p-6"
      />
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
    <section className="rounded-xl border bg-card p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="font-display text-3xl leading-tight font-medium tracking-[-0.01em]">
            {ended ? "Your plan has ended" : "Choose a plan"}
          </h2>
          <p className="text-sm text-muted-foreground">
            Without a plan you get the free check: one a week.
          </p>
        </div>
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
      <div className="mt-6 grid gap-px overflow-hidden rounded-lg border bg-border sm:grid-cols-2">
        {TILES.map((tile) => (
          <div key={tile.id} className="flex flex-col bg-card p-5">
            <p className="text-sm font-semibold">{tile.name}</p>
            <p className="mt-3">
              <span className="font-display text-4xl font-medium tracking-tight">
                {PLAN_PRICE[tile.id]}
              </span>
              <span className="text-sm text-muted-foreground">/month</span>
            </p>
            <p className="mt-1 flex-1 text-sm text-muted-foreground">
              {tile.checks} checks a month, then $1 per extra check.
            </p>
            {billing.checkout_enabled ? (
              <LoadingButton
                className="mt-5"
                variant={tile.id === "starter" ? "default" : "outline"}
                loading={checkout.isPending && checkout.variables === tile.id}
                disabled={checkout.isPending}
                onClick={() => checkout.mutate(tile.id)}
              >
                Subscribe to {tile.name}
              </LoadingButton>
            ) : (
              <Button asChild variant="outline" className="mt-5">
                <a href="/check#contact">Contact us about {tile.name}</a>
              </Button>
            )}
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs text-muted-foreground">
        Prices in Canadian dollars, billed monthly, plus tax where it applies.
        Cancel anytime.
      </p>
    </section>
  )
}
