import { createFileRoute, Link } from "@tanstack/react-router"
import { z } from "zod"
import { CheckStats, ChecksChart } from "@/components/Billing/Overview"
import { PastChecks } from "@/components/Billing/PastChecks"
import { NoPlanCard, PlanCard } from "@/components/Billing/PlanCard"
import { Checker } from "@/components/Check/Checker"
import { planNote } from "@/components/Check/labels"
import { PageHeading } from "@/components/Common/PageHeading"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import { isPaid, useBilling, useRefreshBilling } from "@/hooks/useBilling"
import { useWorkspaces } from "@/hooks/useWorkspace"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout/")({
  component: Checks,
  // A posting's link to check, from a report's "Fix this posting" or the top bar
  validateSearch: z.object({ url: z.string().optional().catch(undefined) }),
  head: () => ({
    meta: [
      {
        title: "Checks - CheckON",
      },
    ],
  }),
})

function greeting(name?: string | null): string {
  const hour = new Date().getHours()
  const part = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening"
  const first = name?.trim().split(" ")[0]
  return `Good ${part}${first ? `, ${first}` : ""}`
}

/** The signed-in page: the plan and how its checks stand, the checker, and past checks. */
function Checks() {
  const { user } = useAuth()
  const { url } = Route.useSearch()
  const { data: billing, isPending } = useBilling()
  const refresh = useRefreshBilling()
  const onPlan = isPaid(billing)
  const { current, canCreate } = useWorkspaces(onPlan)
  const profile = onPlan ? current : undefined
  const history = Boolean(billing?.plan || billing?.has_billing)

  return (
    <div className="flex flex-col gap-4 sm:gap-5">
      <PageHeading title={greeting(user?.full_name)}>
        Signed in as {user?.email}
      </PageHeading>
      {/* A posting's link from a report: the check comes first, the overview after it */}
      <div
        data-dock="Overview"
        className={cn(
          "grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2 xl:grid-cols-3",
          url && "order-2",
        )}
      >
        {isPending || !billing ? (
          <Skeleton className="h-72 rounded-xl md:col-span-2 xl:col-span-3" />
        ) : onPlan ? (
          <PlanCard billing={billing} />
        ) : (
          <div className="md:col-span-2 xl:col-span-3">
            <NoPlanCard billing={billing} />
          </div>
        )}
        {billing?.plan && <CheckStats billing={billing} />}
        {history && (
          <div
            className={cn(
              "flex [&>section]:w-full",
              onPlan
                ? "md:col-span-2 xl:col-span-1"
                : billing?.plan
                  ? "xl:col-span-2"
                  : "md:col-span-2 xl:col-span-3",
            )}
          >
            <ChecksChart />
          </div>
        )}
      </div>
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
      {history && (
        <div className="order-3">
          <PastChecks workspace={canCreate ? profile : undefined} />
        </div>
      )}
    </div>
  )
}
