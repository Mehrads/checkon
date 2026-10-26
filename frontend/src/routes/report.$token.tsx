import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useEffect } from "react"
import { z } from "zod"

import { ReportsService } from "@/client"
import { Report, reportKey } from "@/components/Report/Report"
import { Brand, SiteFooter } from "@/components/Site/Landing"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { isLoggedIn } from "@/hooks/useAuth"
import { noindex } from "@/lib/seo"

export const Route = createFileRoute("/report/$token")({
  component: ReportPage,
  // save=1: back from signing up or logging in on this report, so it's saved to the account
  validateSearch: z.object({
    save: z.union([z.string(), z.number()]).optional().catch(undefined),
  }),
  head: () => ({
    meta: [{ title: "Your posting report - CheckON" }, ...noindex().meta],
  }),
})

/** An outreach report, opened from the link in our email: no sign-in needed to read it. */
function ReportPage() {
  const { token } = Route.useParams()
  const { save } = Route.useSearch()
  const queryClient = useQueryClient()
  const { data, isPending, isError } = useQuery({
    queryKey: reportKey(token),
    queryFn: async () =>
      (await ReportsService.readReport({ path: { token } })).data,
    retry: false,
  })
  const saving = useMutation({
    mutationFn: async () =>
      (await ReportsService.saveReport({ path: { token } })).data,
    onSuccess: (report) => {
      queryClient.setQueryData(reportKey(token), report)
      queryClient.invalidateQueries({ queryKey: ["reports"] })
    },
  })
  const { mutate } = saving
  const unsaved = data && !data.saved
  useEffect(() => {
    if (String(save) === "1" && unsaved && isLoggedIn()) mutate()
  }, [save, unsaved, mutate])

  return (
    <div className="site min-h-svh bg-background text-foreground">
      <header className="border-b bg-background">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between gap-4 px-4 sm:px-6">
          <Brand href="/check" />
          <Button asChild size="sm" variant="ghost">
            <Link to={isLoggedIn() ? "/" : "/login"}>
              {isLoggedIn() ? "Your account" : "Log in"}
            </Link>
          </Button>
        </div>
      </header>
      <main>
        {isPending ? (
          <div className="mx-auto max-w-4xl space-y-6 px-4 py-16 sm:px-6">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : isError || !data ? (
          <div className="mx-auto max-w-xl space-y-4 px-4 py-24 text-center sm:px-6">
            <h1 className="font-display text-3xl font-medium">
              This report isn't available
            </h1>
            <p className="text-muted-foreground">
              The link may be mistyped, or the report was deleted: reports
              nobody saves to an account are deleted after 90 days. You can
              still check any posting yourself.
            </p>
            <Button asChild>
              <a href="/check">Check a posting</a>
            </Button>
          </div>
        ) : (
          <Report report={data} />
        )}
      </main>
      <SiteFooter home="/check" />
    </div>
  )
}
