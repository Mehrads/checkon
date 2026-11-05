import { createFileRoute, Link } from "@tanstack/react-router"

import { PageHeading } from "@/components/Common/PageHeading"
import { ArchiveSetting } from "@/components/Profile/ArchiveSetting"
import { PayBands } from "@/components/Profile/PayBands"
import { ProfileForm } from "@/components/Profile/ProfileForm"
import { Workspaces } from "@/components/Profile/Workspaces"
import { Skeleton } from "@/components/ui/skeleton"
import { useWorkspaces } from "@/hooks/useWorkspace"

export const Route = createFileRoute("/_layout/profile")({
  component: Profile,
  head: () => ({
    meta: [
      {
        title: "Company profile - CheckON",
      },
    ],
  }),
})

/** The company profile every check starts from; with client workspaces, one per client. */
function Profile() {
  const { workspaces, current, canCreate, clients } = useWorkspaces(true)

  return (
    <div className="flex flex-col gap-8">
      <PageHeading title={clients ? "Client workspaces" : "Company profile"}>
        {clients
          ? "A company profile for each client. Checks use the one you pick."
          : "Each check starts from these facts, so it doesn't ask for them."}
      </PageHeading>
      {!current ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <>
          <div data-dock={clients ? "Clients" : "Workspaces"}>
            <Workspaces
              workspaces={workspaces}
              current={current}
              canCreate={canCreate}
            />
          </div>
          <div data-dock="Company profile" className="space-y-3">
            {clients && (
              <h2 className="font-display text-2xl font-medium tracking-[-0.01em]">
                Company profile for {current.name}
              </h2>
            )}
            <ProfileForm key={current.id} profile={current} />
          </div>
          <div data-dock="Archive">
            <ArchiveSetting
              key={current.id}
              profile={current}
              client={clients}
            />
          </div>
          <div data-dock="Pay ranges">
            <PayBands workspaceId={current.id} />
          </div>
          <p className="text-xs text-muted-foreground">
            {current.archive_postings
              ? "These company facts and pay ranges are stored with your account. This workspace's archive is on: the posting is saved when you apply fixes."
              : "These company facts and pay ranges are stored with your account, and never your postings."}{" "}
            <Link to="/privacy" className="underline underline-offset-4">
              Privacy
            </Link>
          </p>
        </>
      )}
    </div>
  )
}
