import { Link } from "@tanstack/react-router"
import { useState } from "react"

import type { AuditSummary, WorkspacePublic } from "@/client"
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
import { useAudits } from "@/hooks/useAudits"
import { formatDay } from "../Billing/UsageMeter"
import { shortAddress } from "./summary"

const RESULTS: [string[], string][] = [
  [["compliant"], "meet the rules"],
  [["not_compliant"], "need changes"],
  [["needs_input"], "need answers"],
  [["not_applicable"], "not covered"],
  [["refused", "failed"], "not checked"],
  [["queued", "checking"], "waiting"],
]

function results(audit: AuditSummary): string {
  return RESULTS.map(([statuses, label]) => {
    const n = statuses.reduce(
      (sum, status) => sum + (audit.statuses[status] ?? 0),
      0,
    )
    return n ? `${n} ${label}` : ""
  })
    .filter(Boolean)
    .join(" · ")
}

/** Past careers page audits: date, page, results. With client workspaces (Agency), the picked `workspace`'s, or
 * every client's. */
export function PastAudits({ workspace }: { workspace?: WorkspacePublic }) {
  const [everyClient, setEveryClient] = useState(false)
  const only = workspace && !everyClient ? workspace : undefined
  const { data, isPending } = useAudits(only?.id)
  const clientColumn = Boolean(workspace) && !only
  return (
    <section className="space-y-2">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="font-display text-2xl font-medium tracking-[-0.01em]">
          {only ? `Past audits for ${only.name}` : "Past audits"}
        </h2>
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
          No audits yet.
        </p>
      ) : (
        <div className="rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                {clientColumn && <TableHead>Client</TableHead>}
                <TableHead>Page</TableHead>
                <TableHead>Postings</TableHead>
                <TableHead>Results</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.data.map((audit) => (
                <TableRow key={audit.id}>
                  <TableCell className="whitespace-nowrap">
                    {formatDay(audit.created_at)}
                  </TableCell>
                  {clientColumn && (
                    <TableCell className="max-w-48 truncate">
                      {audit.workspace_name ?? "—"}
                    </TableCell>
                  )}
                  <TableCell className="max-w-72 truncate font-medium">
                    <Link
                      to="/audits/$auditId"
                      params={{ auditId: audit.id }}
                      search={{}}
                      className="underline-offset-4 hover:underline"
                    >
                      {audit.board_name ?? shortAddress(audit.url)}
                    </Link>
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {audit.postings}
                  </TableCell>
                  <TableCell className="whitespace-normal text-muted-foreground">
                    {results(audit)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {data.count > data.data.length && (
            <p className="border-t px-4 py-2 text-xs text-muted-foreground">
              Showing the latest {data.data.length} of {data.count} audits.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
