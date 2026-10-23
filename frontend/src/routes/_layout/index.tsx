import { createFileRoute, Link } from "@tanstack/react-router"
import { PastChecks } from "@/components/Billing/PastChecks"
import { NoPlanCard, PlanCard } from "@/components/Billing/PlanCard"
import { Checker } from "@/components/Check/Checker"
import { planNote } from "@/components/Check/labels"
import { PageHeading } from "@/components/Common/PageHeading"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import { useBilling, useRefreshBilling } from "@/hooks/useBilling"
import { useWorkspaces } from "@/hooks/useWorkspace"

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

/** The signed-in page: the plan and its checks this period, the checker, and past checks. */
function Checks() {
  const { user } = useAuth()
  const { data: billing, isPending } = useBilling()
  const refresh = useRefreshBilling()
  const onPlan = Boolean(billing?.plan)
  const { current, canCreate } = useWorkspaces(onPlan)
  const profile = onPlan ? current : undefined

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
      {(onPlan || billing?.has_billing) && (
        <PastChecks workspace={canCreate ? profile : undefined} />
      )}
    </div>
  )
}
