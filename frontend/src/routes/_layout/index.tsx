import { createFileRoute, Link } from "@tanstack/react-router"
import { z } from "zod"
import { PastChecks } from "@/components/Billing/PastChecks"
import { NoPlanCard, PlanCard } from "@/components/Billing/PlanCard"
import { Checker } from "@/components/Check/Checker"
import { planNote } from "@/components/Check/labels"
import { PageHeading } from "@/components/Common/PageHeading"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import { isPaid, useBilling, useRefreshBilling } from "@/hooks/useBilling"
import { useWorkspaces } from "@/hooks/useWorkspace"

export const Route = createFileRoute("/_layout/")({
  component: Checks,
  // A posting's link to check, from a report's "Fix this posting"
  validateSearch: z.object({ url: z.string().optional().catch(undefined) }),
  head: () => ({
    meta: [
      {
        title: "Checks - CheckON",
      },
    ],
  }),
})

/** The signed-in page: the plan and its checks this period, the checker, and past checks. */
function Checks() {
  const { user } = useAuth()
  const { url } = Route.useSearch()
  const { data: billing, isPending } = useBilling()
  const refresh = useRefreshBilling()
  const onPlan = isPaid(billing)
  const { current, canCreate } = useWorkspaces(onPlan)
  const profile = onPlan ? current : undefined

  const plan =
    isPending || !billing ? (
      <Skeleton className="h-36 w-full" />
    ) : onPlan ? (
      <PlanCard billing={billing} />
    ) : (
      <NoPlanCard billing={billing} />
    )
  return (
    <div className="flex flex-col gap-8">
      <PageHeading eyebrow="Your account" title="Check a posting">
        Signed in as {user?.email}
      </PageHeading>
      {/* A posting's link from a report: the check comes first, the plan after it */}
      <div className={url ? "order-2" : undefined}>{plan}</div>
      <Checker
        key={url}
        layout="app"
        initialUrl={url}
        note={
          billing?.plan_name
            ? planNote(billing.plan_name, Boolean(profile?.archive_postings))
            : undefined
        }
        onChecked={refresh}
        profile={profile}
        client={canCreate}
        editProfile={(label) => (
          <Link to="/profile" className="underline underline-offset-4">
            {label}
          </Link>
        )}
      />
      {(billing?.plan || billing?.has_billing) && (
        <div className="order-3">
          <PastChecks workspace={canCreate ? profile : undefined} />
        </div>
      )}
    </div>
  )
}
