import { createFileRoute, Link } from "@tanstack/react-router"

import { shortAddress } from "@/components/Audit/summary"
import { formatDay } from "@/components/Billing/UsageMeter"
import { PageHeading } from "@/components/Common/PageHeading"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useMyReports } from "@/hooks/useReports"

export const Route = createFileRoute("/_layout/reports")({
  component: Reports,
  head: () => ({ meta: [{ title: "Reports - CheckON" }] }),
})

/** The reports we sent that the customer saved to their account. */
function Reports() {
  const { data, isPending } = useMyReports()
  return (
    <div className="flex flex-col gap-8">
      <PageHeading title="Reports">
        Reports on your job board that you saved here. Open one to fix its
        postings.
      </PageHeading>
      {isPending ? (
        <Skeleton className="h-32 w-full" />
      ) : !data?.length ? (
        <p className="text-sm text-muted-foreground">
          No reports yet. When we send you a report on your postings, "Save to
          my account" keeps it here.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-card shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead>Board</TableHead>
                <TableHead>Checked</TableHead>
                <TableHead>Postings</TableHead>
                <TableHead>May need changes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((report) => (
                <TableRow key={report.token}>
                  <TableCell>
                    <Link
                      to="/report/$token"
                      params={{ token: report.token }}
                      className="font-medium underline-offset-4 hover:underline"
                    >
                      {report.company}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {shortAddress(report.url)}
                  </TableCell>
                  <TableCell>{formatDay(report.created_at)}</TableCell>
                  <TableCell className="tabular-nums">
                    {report.postings}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {report.to_fix}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
