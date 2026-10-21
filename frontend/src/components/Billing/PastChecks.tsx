import type { Status } from "@/client"
import { StatusLabel } from "@/components/Check/StatusIcon"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { usePaidChecks } from "@/hooks/useBilling"
import { formatDay } from "./UsageMeter"

/** Checks that counted against the plan: date, job title and result. The postings themselves aren't kept. */
export function PastChecks() {
  const { data, isPending } = usePaidChecks()
  return (
    <section className="space-y-2">
      <div>
        <h2 className="text-lg font-semibold">Past checks</h2>
        <p className="text-sm text-muted-foreground">
          The date, job title and result of each check on your plan. We don't
          keep the postings.
        </p>
      </div>
      {isPending ? (
        <Skeleton className="h-24 w-full" />
      ) : !data?.data.length ? (
        <p className="rounded-xl border bg-card p-5 text-sm text-muted-foreground">
          No checks on your plan yet.
        </p>
      ) : (
        <div className="rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Job title</TableHead>
                <TableHead>Result</TableHead>
                <TableHead>After fixes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.data.map((check) => (
                <TableRow key={check.id}>
                  <TableCell className="whitespace-nowrap">
                    {formatDay(check.created_at)}
                    {check.extra && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        extra
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="max-w-64 truncate font-medium">
                    {check.title ?? "Untitled posting"}
                  </TableCell>
                  <TableCell>
                    <StatusLabel status={check.status as Status} />
                  </TableCell>
                  <TableCell>
                    {check.final_status ? (
                      <StatusLabel status={check.final_status as Status} />
                    ) : (
                      <span className="text-muted-foreground">Not applied</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {data.count > data.data.length && (
            <p className="border-t px-4 py-2 text-xs text-muted-foreground">
              Showing the latest {data.data.length} of {data.count} checks.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
