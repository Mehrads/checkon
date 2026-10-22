import { useState } from "react"

import type { Status, WorkspacePublic } from "@/client"
import { StatusLabel } from "@/components/Check/StatusIcon"
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
import { usePaidChecks } from "@/hooks/useBilling"
import { formatDay } from "./UsageMeter"

/** Checks that counted against the plan: date, job title and result. The postings themselves aren't kept.
 * With client workspaces (Agency), the picked `workspace`'s checks, or every client's. */
export function PastChecks({ workspace }: { workspace?: WorkspacePublic }) {
  const [everyClient, setEveryClient] = useState(false)
  const only = workspace && !everyClient ? workspace : undefined
  const { data, isPending } = usePaidChecks(only?.id)
  const clientColumn = Boolean(workspace) && !only
  return (
    <section className="space-y-2">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-medium tracking-[-0.01em]">
            {only ? `Past checks for ${only.name}` : "Past checks"}
          </h2>
          <p className="text-sm text-muted-foreground">
            The date, job title and result of each check on your plan. We don't
            keep the postings.
          </p>
        </div>
        {workspace && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEveryClient(!everyClient)}
          >
            {everyClient ? `Only ${workspace.name}` : "All clients"}
          </Button>
        )}
      </div>
      {isPending ? (
        <Skeleton className="h-24 w-full" />
      ) : !data?.data.length ? (
        <p className="rounded-xl border bg-card p-5 text-sm text-muted-foreground">
          {only
            ? `No checks for ${only.name} yet.`
            : "No checks on your plan yet."}
        </p>
      ) : (
        <div className="rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                {clientColumn && <TableHead>Client</TableHead>}
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
                  {clientColumn && (
                    <TableCell className="max-w-48 truncate">
                      {check.workspace_name ?? "—"}
                    </TableCell>
                  )}
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
