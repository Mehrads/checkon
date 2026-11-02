import { createFileRoute, Link } from "@tanstack/react-router"

import { NewAudit } from "@/components/Audit/NewAudit"
import { PastAudits } from "@/components/Audit/PastAudits"
import { PageHeading } from "@/components/Common/PageHeading"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { isPaid, useBilling } from "@/hooks/useBilling"
import { useWorkspaces } from "@/hooks/useWorkspace"

export const Route = createFileRoute("/_layout/audits/")({
  component: Audits,
  head: () => ({
    meta: [
      {
        title: "Careers page audit - CheckON",
      },
    ],
  }),
})

/** Check every open Ontario posting on a careers page or job board at once, for the current workspace. */
function Audits() {
  const { data: billing, isPending } = useBilling()
  const onPlan = isPaid(billing)
  const { current, canCreate } = useWorkspaces(onPlan)

  return (
    <div className="flex flex-col gap-8">
      <PageHeading title="Audit a careers page">
        {canCreate && current
          ? `Check every open Ontario posting on ${current.name}'s job board at once.`
          : "Check every open Ontario posting on your job board at once."}
      </PageHeading>
      {isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : !onPlan ? (
        <section className="rounded-xl border bg-card p-5 shadow-sm sm:p-6">
          <h2 className="font-display text-2xl font-medium">
            Careers page audits come with a paid plan
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            On Starter or Agency, check every open posting on a careers page in
            one go. Each posting uses one check.
          </p>
          <Button asChild variant="outline" className="mt-4">
            <Link to="/">See the plans</Link>
          </Button>
        </section>
      ) : !current ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <>
          <div data-dock="New audit">
            <NewAudit
              key={current.id}
              workspace={canCreate ? current : undefined}
            />
          </div>
          <div data-dock="Past audits">
            <PastAudits workspace={canCreate ? current : undefined} />
          </div>
        </>
      )}
    </div>
  )
}
