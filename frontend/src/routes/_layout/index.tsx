import { createFileRoute } from "@tanstack/react-router"
import { PastChecks } from "@/components/Billing/PastChecks"
import { NoPlanCard, PlanCard } from "@/components/Billing/PlanCard"
import { Checker } from "@/components/Check/Checker"
import { PageHeading } from "@/components/Common/PageHeading"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import { useBilling, useRefreshBilling } from "@/hooks/useBilling"

export const Route = createFileRoute("/_layout/")({
  component: Checks,
  head: () => ({
    meta: [
      {
        title: "Checks - CheckON",
      },
    ],
  }),
})

const PLAN_NOTE =
  "Each check counts toward your plan. We keep the date, job title and result for your history, never the posting."

/** The signed-in page: the plan and its checks this period, the checker, and past checks. */
function Checks() {
  const { user } = useAuth()
  const { data: billing, isPending } = useBilling()
  const refresh = useRefreshBilling()
  const onPlan = Boolean(billing?.plan)

  return (
    <div className="flex flex-col gap-8">
      <PageHeading eyebrow="Your account" title="Check a posting">
        Signed in as {user?.email}
      </PageHeading>
      {isPending || !billing ? (
        <Skeleton className="h-36 w-full" />
      ) : onPlan ? (
        <PlanCard billing={billing} />
      ) : (
        <NoPlanCard billing={billing} />
      )}
      <Checker
        layout="app"
        note={onPlan ? PLAN_NOTE : undefined}
        onChecked={refresh}
      />
      {(onPlan || billing?.has_billing) && <PastChecks />}
    </div>
  )
}
