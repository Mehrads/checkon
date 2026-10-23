import { Link } from "@tanstack/react-router"
import { Check, Copy, ExternalLink, LoaderCircle } from "lucide-react"
import { useEffect } from "react"

import type { AuditPostingPublic, AuditPublic, Status } from "@/client"
import { ruleName, VERDICT_TEXT } from "@/components/Check/labels"
import { StatusLabel, VerdictIcon } from "@/components/Check/StatusIcon"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useRunAudit } from "@/hooks/useAudits"
import { useRefreshBilling } from "@/hooks/useBilling"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"
import { formatDay } from "../Billing/UsageMeter"
import { group, SOURCE_NAME, shortAddress, summaryLine } from "./summary"

// Audits started from this page load, so React's double effects in development don't start one twice
const started = new Set<string>()

function Result({ posting }: { posting: AuditPostingPublic }) {
  switch (posting.status) {
    case "queued":
      return <span className="text-muted-foreground">Waiting</span>
    case "checking":
      return (
        <span className="inline-flex items-center gap-1.5 text-muted-foreground">
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
          Checking
        </span>
      )
    case "refused":
    case "failed":
      return (
        <span className="text-muted-foreground">
          {posting.status === "refused" ? "Not checked" : "Couldn't check"}
          {posting.note && (
            <span className="block text-xs">{posting.note}</span>
          )}
        </span>
      )
    default:
      return (
        <>
          <StatusLabel status={posting.status as Status} />
          {posting.final_status && (
            <span className="mt-1 block text-xs text-muted-foreground">
              After fixes: <StatusLabel status={posting.final_status} />
            </span>
          )}
        </>
      )
  }
}

function Issues({ posting }: { posting: AuditPostingPublic }) {
  if (!posting.issues.length)
    return group(posting) === "compliant" ? (
      <span className="text-muted-foreground">None</span>
    ) : null
  return (
    <ul className="space-y-1">
      {posting.issues.map((issue) => (
        <li key={issue.rule} className="flex items-center gap-1.5 text-sm">
          <VerdictIcon verdict={issue.verdict} className="size-4" />
          <span>
            {ruleName(issue.rule)}
            <span className="sr-only">: {VERDICT_TEXT[issue.verdict]}</span>
          </span>
        </li>
      ))}
    </ul>
  )
}

/** The audit's postings with their results, checked from this page; a summary line to share. `run`: start checking
 * the postings still waiting as soon as the page opens (right after the customer picked them). */
export function AuditReport({
  audit,
  run,
}: {
  audit: AuditPublic
  run: boolean
}) {
  const refresh = useRefreshBilling()
  const runner = useRunAudit(audit.id, refresh)
  const [copied, copy] = useCopyToClipboard()
  const waiting = audit.postings.filter((p) => p.status === "queued")
  const retry = audit.postings.filter((p) => p.status === "failed")
  const done = audit.postings.filter((p) => group(p) !== "pending").length
  const share = Math.round((done / Math.max(audit.postings.length, 1)) * 100)
  const line = summaryLine(audit)

  useEffect(() => {
    if (run && waiting.length && !started.has(audit.id)) {
      started.add(audit.id)
      runner.run(waiting)
    }
  }, [run, audit.id, waiting, runner])

  return (
    <div className="space-y-6">
      <section className="space-y-4 rounded-xl border bg-card p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate font-display text-2xl font-medium">
              {audit.board_name ?? shortAddress(audit.url)}
            </h2>
            <p className="text-sm text-muted-foreground">
              <a
                href={audit.url}
                target="_blank"
                rel="noreferrer"
                className="underline-offset-4 hover:underline"
              >
                {shortAddress(audit.url)}
              </a>{" "}
              · {formatDay(audit.created_at)}
              {audit.workspace_name && ` · ${audit.workspace_name}`}
              {audit.outside_ontario > 0 &&
                ` · ${audit.outside_ontario} postings outside Ontario left out`}
            </p>
          </div>
          <Badge variant="outline">{SOURCE_NAME[audit.source]}</Badge>
        </div>
        <div className="space-y-2">
          <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
            <p>
              <span className="font-semibold tabular-nums">{done}</span> of{" "}
              <span className="tabular-nums">{audit.postings.length}</span>{" "}
              postings checked
            </p>
            {runner.running ? (
              <Button size="sm" variant="ghost" onClick={runner.stop}>
                Stop after these
              </Button>
            ) : (
              (waiting.length > 0 || retry.length > 0) && (
                <LoadingButton
                  size="sm"
                  loading={runner.running}
                  onClick={() => runner.run([...waiting, ...retry])}
                >
                  Check the {waiting.length + retry.length} left (uses{" "}
                  {waiting.length + retry.length}{" "}
                  {waiting.length + retry.length === 1 ? "check" : "checks"})
                </LoadingButton>
              )
            )}
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label="Postings checked"
            aria-valuemin={0}
            aria-valuemax={audit.postings.length}
            aria-valuenow={done}
          >
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${share}%` }}
            />
          </div>
          {runner.stopped && (
            <p className="text-sm text-destructive">{runner.stopped}</p>
          )}
        </div>
        <div className="rounded-lg border bg-muted/40 p-4">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm">{line}</p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => copy(line)}
              aria-label="Copy the summary"
            >
              {copied ? <Check /> : <Copy />}
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
        </div>
      </section>

      <div className="rounded-xl border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Posting</TableHead>
              <TableHead>Result</TableHead>
              <TableHead>Main issues</TableHead>
              <TableHead className="text-right">Full check</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {audit.postings.map((posting) => (
              <TableRow key={posting.id} className="align-top">
                <TableCell className="max-w-72 whitespace-normal">
                  <a
                    href={posting.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-start gap-1 font-medium underline-offset-4 hover:underline"
                  >
                    {posting.title}
                    <ExternalLink
                      className="mt-1 size-3 shrink-0 text-muted-foreground"
                      aria-label="(opens the posting)"
                    />
                  </a>
                  <span className="block truncate text-xs text-muted-foreground">
                    {posting.location ?? "No location given"}
                    {posting.where === "canada" &&
                      " · may be filled in Ontario"}
                  </span>
                </TableCell>
                <TableCell className="whitespace-normal">
                  <Result posting={posting} />
                </TableCell>
                <TableCell className="whitespace-normal">
                  <Issues posting={posting} />
                </TableCell>
                <TableCell className="text-right">
                  {posting.checked_at &&
                    !["refused", "failed", "checking"].includes(
                      posting.status,
                    ) && (
                      <Link
                        to="/audits/$auditId/$postingId"
                        params={{ auditId: audit.id, postingId: posting.id }}
                        className="text-sm font-medium underline underline-offset-4"
                      >
                        {posting.check_open ? "Open with fixes" : "Check again"}
                      </Link>
                    )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <p className="text-xs text-muted-foreground">
        Each full check, with its fixes, stays open for an hour after it runs.
        We keep each posting's title, place, link and result, never the posting,
        so after that hour a posting is read and checked again (one check).
      </p>
    </div>
  )
}
