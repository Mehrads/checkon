import { Search } from "lucide-react"
import { useState } from "react"

import type { CheckRecordPublic, Status, WorkspacePublic } from "@/client"
import { STATUS_LABEL, StatusLabel } from "@/components/Check/StatusIcon"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useAccountChecks } from "@/hooks/useAccount"
import { useIsMobile } from "@/hooks/useMobile"
import { formatDay } from "@/lib/utils"

// The list stays short enough to scroll past, and "Show more" reveals the rest
const PAGE = 10

/** A phone has no room for the table's columns, so each check is a short block; nothing scrolls sideways. */
function CheckRows({
  checks,
  clientColumn,
}: {
  checks: CheckRecordPublic[]
  clientColumn: boolean
}) {
  return (
    <ul className="divide-y rounded-xl border">
      {checks.map((check) => (
        <li key={check.id} className="space-y-1 p-3 text-sm">
          <p className="truncate font-medium">
            {check.title ?? "Untitled posting"}
          </p>
          <p className="text-xs text-muted-foreground">
            {formatDay(check.created_at)}
            {clientColumn && check.workspace_name
              ? ` · ${check.workspace_name}`
              : ""}
          </p>
          <StatusLabel
            status={(check.final_status ?? check.status) as Status}
          />
        </li>
      ))}
    </ul>
  )
}

/** The account's checks: date, job title and result, to search and filter. Postings are kept only by the archive.
 * With client workspaces, the picked `workspace`'s checks, or every client's. */
export function PastChecks({ workspace }: { workspace?: WorkspacePublic }) {
  const [everyClient, setEveryClient] = useState(false)
  const [search, setSearch] = useState("")
  const [result, setResult] = useState<Status | "all">("all")
  const [shown, setShown] = useState(PAGE)
  const phone = useIsMobile()
  const only = workspace && !everyClient ? workspace : undefined
  const { data, isPending } = useAccountChecks(only?.id)
  const clientColumn = Boolean(workspace) && !only

  const words = search.trim().toLowerCase()
  const matches = (data?.data ?? []).filter(
    (check) =>
      (result === "all" || (check.final_status ?? check.status) === result) &&
      `${check.title ?? ""} ${check.workspace_name ?? ""}`
        .toLowerCase()
        .includes(words),
  )
  const visible = matches.slice(0, shown)

  return (
    <section
      data-dock="Past checks"
      className="space-y-4 rounded-xl border bg-card p-4 shadow-sm sm:p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1 basis-72">
          <h2 className="font-display text-lg font-medium">
            {only ? `Past checks for ${only.name}` : "Past checks"}
          </h2>
          <p className="text-xs text-muted-foreground">
            The date, job title and result of each check on your account. The
            postings themselves are kept only when a workspace's archive is on.
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <div className="relative min-w-0 flex-1 sm:w-52 sm:flex-none">
            <Search
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setShown(PAGE)
              }}
              aria-label="Search past checks"
              placeholder="Search"
              className="h-9 rounded-full pl-9"
            />
          </div>
          <Select
            value={result}
            onValueChange={(value) => {
              setResult(value as Status | "all")
              setShown(PAGE)
            }}
          >
            <SelectTrigger
              size="sm"
              aria-label="Filter past checks by result"
              className="h-9 rounded-full"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent align="end">
              <SelectItem value="all">All results</SelectItem>
              {(Object.keys(STATUS_LABEL) as Status[]).map((status) => (
                <SelectItem key={status} value={status}>
                  {STATUS_LABEL[status]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
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
      </div>
      {isPending ? (
        <Skeleton className="h-24 w-full" />
      ) : !data?.data.length ? (
        <p className="rounded-xl border p-5 text-sm text-muted-foreground">
          {only
            ? `No checks for ${only.name} yet.`
            : "No checks on your account yet."}
        </p>
      ) : !matches.length ? (
        <p className="rounded-xl border p-5 text-sm text-muted-foreground">
          No past checks match that search.
        </p>
      ) : (
        <div className="space-y-3">
          {phone ? (
            <CheckRows checks={visible} clientColumn={clientColumn} />
          ) : (
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
                {visible.map((check) => (
                  <TableRow key={check.id}>
                    <TableCell className="whitespace-nowrap">
                      {formatDay(check.created_at)}
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
                        <span className="text-muted-foreground">
                          Not applied
                        </span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <p>
              Showing {visible.length} of{" "}
              {words || result !== "all"
                ? `${matches.length} matching`
                : data.count}{" "}
              checks.
            </p>
            {shown < matches.length && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShown(shown + PAGE)}
              >
                Show {Math.min(PAGE, matches.length - shown)} more
              </Button>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
