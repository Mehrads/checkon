import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { Archive as ArchiveIcon, Download, Search } from "lucide-react"
import { useDeferredValue, useState } from "react"
import { z } from "zod"

import type { Status } from "@/client"
import {
  ArchivedPostingSheet,
  formatDate,
} from "@/components/Archive/ArchivedPosting"
import { formatDay } from "@/components/Billing/UsageMeter"
import { StatusLabel } from "@/components/Check/StatusIcon"
import { PageHeading } from "@/components/Common/PageHeading"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
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
import { exportArchive, useArchive } from "@/hooks/useArchive"
import { apiMessage, apiStatus, useBilling } from "@/hooks/useBilling"
import useCustomToast from "@/hooks/useCustomToast"

const ALL = "all"

export const Route = createFileRoute("/_layout/archive")({
  component: Archive,
  validateSearch: z.object({ posting: z.string().optional() }),
  head: () => ({
    meta: [
      {
        title: "Archive - CheckON",
      },
    ],
  }),
})

/** The archive of approved postings (paid plans): every posting applied in a workspace with the archive on,
 * kept 3 years after it comes down. Readable, downloadable and deletable after the plan ends. */
function Archive() {
  const { posting } = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const { data: billing, isPending: billingPending } = useBilling()
  const { showErrorToast } = useCustomToast()
  const [workspaceId, setWorkspaceId] = useState(ALL)
  const [title, setTitle] = useState("")
  const [savedFrom, setSavedFrom] = useState("")
  const [savedTo, setSavedTo] = useState("")
  const [exporting, setExporting] = useState(false)
  const q = useDeferredValue(title.trim())
  const { data, isPending, error } = useArchive(
    {
      workspaceId: workspaceId === ALL ? undefined : workspaceId,
      q,
      savedFrom,
      savedTo,
    },
    Boolean(billing), // the API answers 403 to accounts without a customer: no plan, now or before
  )
  const open = (id?: string) =>
    navigate({ search: id ? { posting: id } : {}, replace: !id })

  const workspaces = data?.workspaces ?? []
  const clients = workspaces.length > 1
  // A zip per workspace: the one picked, or the only one
  const zipFor =
    workspaceId !== ALL
      ? workspaceId
      : workspaces.length === 1
        ? workspaces[0].id
        : undefined
  const anyOn = workspaces.some((w) => w.archive_postings)
  const filtered = Boolean(q || savedFrom || savedTo || workspaceId !== ALL)

  const download = async () => {
    if (!zipFor) return
    setExporting(true)
    try {
      await exportArchive(zipFor)
    } catch (err) {
      showErrorToast(
        apiMessage(err as Error, "We couldn't download the archive."),
      )
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeading title="Archive">
        A dated copy of each posting you apply fixes to, kept 3 years after it
        comes down.
      </PageHeading>

      {billingPending ? (
        <Skeleton className="h-48 w-full" />
      ) : error && apiStatus(error) === 403 && !data ? (
        <section className="rounded-xl border bg-card p-5 shadow-sm sm:p-6">
          <h2 className="font-display text-2xl font-medium">
            The archive comes with a paid plan
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            On Starter or Agency, CheckON keeps a dated copy of each posting you
            apply fixes to, with its application form and linked documents.
          </p>
          <Button asChild variant="outline" className="mt-4">
            <Link to="/">See the plans</Link>
          </Button>
        </section>
      ) : (
        <>
          {data?.read_only && (
            <Alert>
              <ArchiveIcon />
              <AlertTitle>Your plan has ended</AlertTitle>
              <AlertDescription>
                Nothing new is saved. You can still view and download your
                archive, mark postings taken down and delete them.
              </AlertDescription>
            </Alert>
          )}
          {data && !data.read_only && !anyOn && (
            <Alert>
              <ArchiveIcon />
              <AlertTitle>The archive is off</AlertTitle>
              <AlertDescription>
                <span>
                  Turn it on in your{" "}
                  <Link to="/profile" className="underline underline-offset-4">
                    {clients ? "client workspaces" : "company profile"}
                  </Link>
                  {clients ? ", for each client," : ""} and each posting you
                  apply fixes to is saved here.
                </span>
              </AlertDescription>
            </Alert>
          )}

          <section className="space-y-3">
            <div className="flex flex-wrap items-end gap-3">
              {clients && (
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Client</span>
                  <Select value={workspaceId} onValueChange={setWorkspaceId}>
                    <SelectTrigger aria-label="Client" className="w-52">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent align="start">
                      <SelectItem value={ALL}>All clients</SelectItem>
                      {workspaces.map((w) => (
                        <SelectItem key={w.id} value={w.id}>
                          {w.name}
                          {w.archived ? " (archived)" : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              <div className="min-w-48 flex-1 space-y-1">
                <Label
                  htmlFor="archive-title"
                  className="text-xs font-normal text-muted-foreground"
                >
                  Job title
                </Label>
                <div className="relative">
                  <Search
                    className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    id="archive-title"
                    type="search"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder="Search job titles"
                    className="pl-8"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <Label
                  htmlFor="archive-from"
                  className="text-xs font-normal text-muted-foreground"
                >
                  Saved from
                </Label>
                <Input
                  id="archive-from"
                  type="date"
                  value={savedFrom}
                  max={savedTo || undefined}
                  onChange={(event) => setSavedFrom(event.target.value)}
                  className="w-40"
                />
              </div>
              <div className="space-y-1">
                <Label
                  htmlFor="archive-to"
                  className="text-xs font-normal text-muted-foreground"
                >
                  to
                </Label>
                <Input
                  id="archive-to"
                  type="date"
                  value={savedTo}
                  min={savedFrom || undefined}
                  onChange={(event) => setSavedTo(event.target.value)}
                  className="w-40"
                />
              </div>
              <LoadingButton
                variant="outline"
                loading={exporting}
                disabled={!zipFor}
                title={
                  zipFor ? undefined : "Pick a client to download its archive"
                }
                onClick={download}
              >
                <Download /> Download zip
              </LoadingButton>
            </div>
            {clients && !zipFor && (
              <p className="text-xs text-muted-foreground">
                Pick a client to download its archive as a zip.
              </p>
            )}

            {isPending ? (
              <Skeleton className="h-32 w-full" />
            ) : !data?.data.length ? (
              <p className="rounded-xl border bg-card p-5 text-sm text-muted-foreground">
                {filtered
                  ? "No archived postings match."
                  : data?.read_only
                    ? "No postings in the archive."
                    : "No postings in the archive yet. Apply fixes to a check and it's saved here."}
              </p>
            ) : (
              <div className="rounded-xl border bg-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Saved</TableHead>
                      {clients && workspaceId === ALL && (
                        <TableHead>Client</TableHead>
                      )}
                      <TableHead>Job title</TableHead>
                      <TableHead>Result</TableHead>
                      <TableHead>Taken down</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.data.map((row) => (
                      <TableRow
                        key={row.id}
                        className="cursor-pointer"
                        onClick={() => open(row.id)}
                      >
                        <TableCell className="whitespace-nowrap">
                          {formatDay(row.created_at)}
                        </TableCell>
                        {clients && workspaceId === ALL && (
                          <TableCell className="max-w-48 truncate">
                            {row.workspace_name}
                          </TableCell>
                        )}
                        <TableCell className="max-w-64 truncate font-medium">
                          <button
                            type="button"
                            className="max-w-full truncate text-left underline-offset-4 hover:underline"
                            onClick={(event) => {
                              event.stopPropagation()
                              open(row.id)
                            }}
                          >
                            {row.title ?? "Untitled posting"}
                          </button>
                          {row.files > 0 && (
                            <span className="ml-2 text-xs font-normal text-muted-foreground">
                              {row.files}{" "}
                              {row.files === 1 ? "document" : "documents"}
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          {row.final_status ? (
                            <StatusLabel status={row.final_status as Status} />
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {row.taken_down_on && row.kept_until ? (
                            <>
                              {formatDate(row.taken_down_on)}
                              <span className="block text-xs text-muted-foreground">
                                Kept until {formatDate(row.kept_until)}
                              </span>
                            </>
                          ) : (
                            <span className="text-muted-foreground">
                              Still up
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {data.count > data.data.length && (
                  <p className="border-t px-4 py-2 text-xs text-muted-foreground">
                    Showing the latest {data.data.length} of {data.count}{" "}
                    postings. Search to find older ones.
                  </p>
                )}
              </div>
            )}
          </section>
        </>
      )}
      <ArchivedPostingSheet id={posting} onClose={() => open()} />
    </div>
  )
}
