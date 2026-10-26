import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Copy } from "lucide-react"

import { ReportsService, UsersService } from "@/client"
import { formatDay } from "@/components/Billing/UsageMeter"
import { PageHeading } from "@/components/Common/PageHeading"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"

export const Route = createFileRoute("/_layout/outreach")({
  component: Outreach,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({ meta: [{ title: "Outreach - CheckON" }] }),
})

/** Every report the outreach workflow saved: whether the company opened it, and whether they saved it. */
function Outreach() {
  const { data, isPending } = useQuery({
    queryKey: ["outreachReports"],
    queryFn: async () => (await ReportsService.readOutreachReports()).data,
  })
  const [copied, copy] = useCopyToClipboard()
  return (
    <div className="flex flex-col gap-8">
      <PageHeading eyebrow="Admin" title="Outreach">
        The reports linked from outreach emails, newest first. Opening one
        yourself while signed in isn't counted as a view.
      </PageHeading>
      {isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : !data?.length ? (
        <p className="text-sm text-muted-foreground">
          No reports yet. The outreach workflow saves one per company it
          pitches.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-card shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead>Made</TableHead>
                <TableHead>Postings</TableHead>
                <TableHead>May need changes</TableHead>
                <TableHead>Views</TableHead>
                <TableHead>First opened</TableHead>
                <TableHead>Saved by</TableHead>
                <TableHead>
                  <span className="sr-only">Link</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((report) => {
                const link = `${window.location.origin}/report/${report.token}`
                return (
                  <TableRow key={report.token}>
                    <TableCell>
                      <a
                        href={link}
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium underline-offset-4 hover:underline"
                      >
                        {report.company}
                      </a>
                    </TableCell>
                    <TableCell>{formatDay(report.created_at)}</TableCell>
                    <TableCell className="tabular-nums">
                      {report.postings}
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {report.to_fix}
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {report.views}
                    </TableCell>
                    <TableCell>
                      {report.first_viewed_at
                        ? formatDay(report.first_viewed_at)
                        : "Not yet"}
                    </TableCell>
                    <TableCell>{report.saved_by ?? "Not saved"}</TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copy(link)}
                      >
                        <Copy />
                        {copied === link ? "Copied" : "Copy link"}
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
