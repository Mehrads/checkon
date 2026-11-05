import { useNavigate } from "@tanstack/react-router"
import { ArrowRight, ExternalLink, ShieldCheck } from "lucide-react"
import { useState } from "react"

import type { FoundPublic, PreviewOut, WorkspacePublic } from "@/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { usePreviewAudit, useStartAudit } from "@/hooks/useAudits"
import { apiMessage } from "@/lib/api"
import { SOURCE_NAME, shortAddress } from "./summary"

function plural(n: number, one: string, many = `${one}s`): string {
  return `${n.toLocaleString()} ${n === 1 ? one : many}`
}

/** The checks the picked postings will use, and whether the account has that many left when the server limits
 * them (`checks_left`; null: no limit). */
function Cost({ found, picked }: { found: PreviewOut; picked: number }) {
  const left = found.checks_left
  if (left != null && picked > left)
    return (
      <p className="text-sm text-destructive">
        You have {plural(left, "check")} left for the last 30 days. Pick fewer
        postings.
      </p>
    )
  return (
    <p className="text-sm text-muted-foreground">
      Uses{" "}
      <strong className="text-foreground">{plural(picked, "check")}</strong>
      {left == null ? "." : ` of the ${plural(left, "check")} you have left.`}
    </p>
  )
}

function Posting({
  posting,
  checked,
  onChange,
}: {
  posting: FoundPublic
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <li className="flex items-start gap-3 px-4 py-3">
      <Checkbox
        id={`posting-${posting.id}`}
        checked={checked}
        onCheckedChange={(value) => onChange(value === true)}
        className="mt-0.5"
      />
      <label
        htmlFor={`posting-${posting.id}`}
        className="min-w-0 flex-1 cursor-pointer"
      >
        <span className="block font-medium">{posting.title}</span>
        <span className="block truncate text-sm text-muted-foreground">
          {posting.location ?? "No location given"}
          {posting.where === "canada" && " · may be filled in Ontario"}
        </span>
      </label>
      <a
        href={posting.url}
        target="_blank"
        rel="noreferrer"
        className="mt-0.5 text-muted-foreground hover:text-foreground"
        aria-label={`Open ${posting.title} on the job board`}
      >
        <ExternalLink className="size-4" />
      </a>
    </li>
  )
}

/** The postings found and the checks they'll use; nothing runs until "Check". Ontario postings start ticked;
 * Canada-wide ones may be filled in Ontario, so they're listed unticked. */
function Found({
  found,
  client,
  onCancel,
}: {
  found: PreviewOut
  client: boolean
  onCancel: () => void
}) {
  const navigate = useNavigate()
  const start = useStartAudit()
  const [picked, setPicked] = useState<Set<string>>(
    () =>
      new Set(
        found.postings
          .filter((p) => p.where === "ontario")
          .slice(0, found.max_postings)
          .map((p) => p.id),
      ),
  )
  const toggle = (id: string, on: boolean) =>
    setPicked((current) => {
      const next = new Set(current)
      if (on) next.add(id)
      else next.delete(id)
      return next
    })
  const where = found.board_name ?? shortAddress(found.url)
  const tooMany = picked.size > found.max_postings
  const overLimit = found.checks_left != null && picked.size > found.checks_left
  const all = found.postings.length > 0 && picked.size === found.postings.length
  const inOntario = found.postings.filter((p) => p.where === "ontario").length
  const canadaWide = found.postings.length - inOntario

  if (!found.postings.length)
    return (
      <section className="space-y-3 rounded-xl border bg-card p-5 shadow-sm sm:p-6">
        <h2 className="font-display text-2xl font-medium">
          No open postings in Ontario on {where}
        </h2>
        <p className="text-sm text-muted-foreground">
          We found {plural(found.outside_ontario, "posting")}, all for work
          outside Ontario, so there's nothing to check.
        </p>
        <Button variant="outline" onClick={onCancel}>
          Try another address
        </Button>
      </section>
    )

  return (
    <section className="space-y-4 rounded-xl border bg-card p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display text-2xl font-medium">
            {inOntario
              ? `${plural(inOntario, "open posting")} in Ontario on ${where}`
              : `${plural(canadaWide, "open posting")} for anywhere in Canada on ${where}`}
          </h2>
          <p className="text-sm text-muted-foreground">
            {inOntario > 0 &&
              canadaWide > 0 &&
              `${plural(canadaWide, "more posting")} for anywhere in Canada may be filled in Ontario: tick them to check them too. `}
            {found.outside_ontario > 0 &&
              `${plural(found.outside_ontario, "posting")} for work outside Ontario left out. `}
            {client
              ? `Checks use ${found.workspace_name}'s company profile.`
              : "Checks use your company profile."}
          </p>
        </div>
        <Badge variant="outline">{SOURCE_NAME[found.source]}</Badge>
      </div>

      <div className="rounded-lg border">
        <div className="flex items-center gap-3 border-b px-4 py-2 text-sm">
          <Checkbox
            id="pick-all"
            checked={all}
            onCheckedChange={(value) =>
              setPicked(
                new Set(value === true ? found.postings.map((p) => p.id) : []),
              )
            }
          />
          <label
            htmlFor="pick-all"
            className="cursor-pointer text-muted-foreground"
          >
            {plural(picked.size, "posting")} picked
          </label>
        </div>
        <ul className="max-h-[28rem] divide-y overflow-y-auto">
          {found.postings.map((posting) => (
            <Posting
              key={posting.id}
              posting={posting}
              checked={picked.has(posting.id)}
              onChange={(on) => toggle(posting.id, on)}
            />
          ))}
        </ul>
        {found.more > 0 && (
          <p className="border-t px-4 py-2 text-xs text-muted-foreground">
            And {plural(found.more, "more posting")}. Check these first, then
            run another audit for the rest.
          </p>
        )}
      </div>

      {tooMany ? (
        <p className="text-sm text-destructive">
          One audit checks up to {found.max_postings} postings. Untick{" "}
          {picked.size - found.max_postings}.
        </p>
      ) : (
        <Cost found={found} picked={picked.size} />
      )}
      {start.error && (
        <p className="text-sm text-destructive">
          {apiMessage(start.error, "We couldn't start the audit. Try again.")}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <LoadingButton
          loading={start.isPending}
          disabled={!picked.size || tooMany || overLimit}
          onClick={() =>
            start.mutate(
              { preview_id: found.preview_id, posting_ids: [...picked] },
              {
                onSuccess: (audit) =>
                  navigate({
                    to: "/audits/$auditId",
                    params: { auditId: audit.id },
                    search: { run: true },
                  }),
              },
            )
          }
        >
          Check {plural(picked.size, "posting")} <ArrowRight />
        </LoadingButton>
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </section>
  )
}

/** Enter a careers page or job board; see its open Ontario postings and what checking them uses. */
export function NewAudit({ workspace }: { workspace?: WorkspacePublic }) {
  const [url, setUrl] = useState("")
  const preview = usePreviewAudit()

  if (preview.data)
    return (
      <Found
        key={preview.data.preview_id}
        found={preview.data}
        client={Boolean(workspace)}
        onCancel={() => preview.reset()}
      />
    )

  return (
    <section className="rounded-2xl border bg-card p-5 shadow-sm sm:p-6">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          preview.mutate({ url, workspace_id: workspace?.id })
        }}
      >
        <label htmlFor="careers-url" className="text-sm font-medium">
          Your careers page or job board
        </label>
        <p className="text-xs text-muted-foreground">
          A Greenhouse, Lever, Ashby or SmartRecruiters board, or the page on
          your site that lists your openings.
        </p>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
          <Input
            id="careers-url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://jobs.lever.co/yourcompany"
            inputMode="url"
            autoComplete="url"
            maxLength={2048}
            className="h-10"
          />
          <LoadingButton
            type="submit"
            size="lg"
            loading={preview.isPending}
            disabled={!url.trim()}
          >
            Find postings <ArrowRight />
          </LoadingButton>
        </div>
      </form>
      {preview.isPending && (
        <p className="mt-3 text-sm text-muted-foreground">
          Reading the job board. A careers page with many links can take a
          minute.
        </p>
      )}
      {preview.error && (
        <Alert variant="destructive" className="mt-4">
          <AlertTitle>We couldn't read that page</AlertTitle>
          <AlertDescription>
            {apiMessage(preview.error, "Something went wrong. Try again.")}
          </AlertDescription>
        </Alert>
      )}
      <p className="mt-4 flex items-start gap-2 border-t pt-4 text-xs text-muted-foreground">
        <ShieldCheck
          className="mt-px size-4 shrink-0 text-primary"
          aria-hidden="true"
        />
        Nothing is checked until you pick the postings. We read each one from
        your public board when we check it, follow the site's robots.txt, and
        keep its title, place, link and result, never the posting.
      </p>
    </section>
  )
}
