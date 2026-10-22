import { createFileRoute, Link } from "@tanstack/react-router"

import { PageHeading } from "@/components/Common/PageHeading"
import { ProfileForm } from "@/components/Profile/ProfileForm"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useBilling } from "@/hooks/useBilling"
import { useWorkspace } from "@/hooks/useWorkspace"

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

/** The company profile every check starts from (paid plans). */
function Profile() {
  const { data: billing, isPending } = useBilling()
  const onPlan = Boolean(billing?.plan)
  const { data: profile } = useWorkspace(onPlan)

  return (
    <div className="flex flex-col gap-8">
      <PageHeading eyebrow="Your account" title="Company profile">
        Each check starts from these facts, so it doesn't ask for them.
      </PageHeading>
      {isPending ? (
        <Skeleton className="h-96 w-full" />
      ) : !onPlan ? (
        <section className="rounded-xl border bg-card p-5 shadow-sm sm:p-6">
          <h2 className="font-display text-2xl font-medium">
            A company profile comes with a paid plan
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            On Starter or Agency, your checks start from your company's details
            instead of asking for them.
          </p>
          <Button asChild variant="outline" className="mt-4">
            <Link to="/">See the plans</Link>
          </Button>
        </section>
      ) : !profile ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <>
          <ProfileForm key={profile.id} profile={profile} />
          <p className="text-xs text-muted-foreground">
            We store these company facts with your account, and never your
            postings.{" "}
            <Link to="/privacy" className="underline underline-offset-4">
              Privacy
            </Link>
          </p>
        </>
      )}
    </div>
  )
}
