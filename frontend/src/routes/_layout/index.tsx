import { createFileRoute, Link } from "@tanstack/react-router"
import { z } from "zod"
import { CheckStats, ChecksChart } from "@/components/Account/Overview"
import { PastChecks } from "@/components/Account/PastChecks"
import { usageText } from "@/components/Account/usage"
import { Checker } from "@/components/Check/Checker"
import { accountNote } from "@/components/Check/labels"
import { PageHeading } from "@/components/Common/PageHeading"
import { Skeleton } from "@/components/ui/skeleton"
import { useAccount, useRefreshAccount } from "@/hooks/useAccount"
import useAuth from "@/hooks/useAuth"
import { useWorkspaces } from "@/hooks/useWorkspace"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout/")({
  component: Checks,
  // A posting's link to check, from the top bar
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

/** The signed-in page: the account's checks and how they stand, the checker, and past checks. */
function Checks() {
  const { user } = useAuth()
  const { url } = Route.useSearch()
  const { data: account } = useAccount()
  const refresh = useRefreshAccount()
  const { current, clients } = useWorkspaces(true)

  return (
    <div className="flex flex-col gap-4 sm:gap-5">
      <PageHeading title={greeting(user?.full_name)}>
        Signed in as {user?.email}
        {account && ` · ${usageText(account)}`}
      </PageHeading>
      {/* A posting's link from the top bar: the check comes first, the overview after it */}
      <div
        data-dock="Overview"
        className={cn(
          "grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2 xl:grid-cols-3",
          url && "order-2",
        )}
      >
        {account ? (
          <CheckStats account={account} />
        ) : (
          <Skeleton className="h-72 rounded-xl" />
        )}
        <div className="flex xl:col-span-2 [&>section]:w-full">
          <ChecksChart />
        </div>
      </div>
      <Checker
        key={url}
        layout="app"
        initialUrl={url}
        note={accountNote(Boolean(current?.archive_postings))}
        onChecked={refresh}
        profile={current}
        client={clients}
        editProfile={(label) => (
          <Link to="/profile" className="underline underline-offset-4">
            {label}
          </Link>
        )}
      />
      <div className="order-3">
        <PastChecks workspace={clients ? current : undefined} />
      </div>
    </div>
  )
}
