import { createFileRoute } from "@tanstack/react-router"

import { NewAudit } from "@/components/Audit/NewAudit"
import { PastAudits } from "@/components/Audit/PastAudits"
import { PageHeading } from "@/components/Common/PageHeading"
import { Skeleton } from "@/components/ui/skeleton"
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
  const { current, clients } = useWorkspaces(true)

  return (
    <div className="flex flex-col gap-8">
      <PageHeading title="Audit a careers page">
        {clients && current
          ? `Check every open Ontario posting on ${current.name}'s job board at once.`
          : "Check every open Ontario posting on your job board at once."}
      </PageHeading>
      {!current ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <>
          <div data-dock="New audit">
            <NewAudit
              key={current.id}
              workspace={clients ? current : undefined}
            />
          </div>
          <div data-dock="Past audits">
            <PastAudits workspace={clients ? current : undefined} />
          </div>
        </>
      )}
    </div>
  )
}
