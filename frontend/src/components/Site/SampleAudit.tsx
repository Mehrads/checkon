import { Link } from "@tanstack/react-router"
import { AxiosError } from "axios"
import { ArrowRight, ExternalLink, LoaderCircle } from "lucide-react"
import { useState } from "react"
import {
  AuditsService,
  type SampleOut,
  type SamplePosting,
  type Status,
} from "@/client"
import { shortAddress } from "@/components/Audit/summary"
import { ruleName } from "@/components/Check/labels"
import { StatusLabel, VerdictIcon } from "@/components/Check/StatusIcon"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { isLoggedIn } from "@/hooks/useAuth"
import { apiMessage } from "@/hooks/useBilling"
import { track } from "@/lib/analytics"
import { Heading, Kicker } from "./Landing"

function reason(error: unknown): string {
  return error instanceof AxiosError
    ? (error.response?.data?.detail?.reason ??
        String(error.response?.status ?? "network"))
    : "unknown"
}

function Result({ posting }: { posting: SamplePosting }) {
  const findings = posting.findings ?? []
  return (
    <li className="space-y-3 px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
        <div className="min-w-0">
          <a
            href={posting.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-start gap-1 font-medium underline-offset-4 hover:underline"
          >
            {posting.title}
            <ExternalLink
              className="mt-1 size-3 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
          </a>
          <p className="truncate text-sm text-muted-foreground">
            {posting.location ?? "No location given"}
          </p>
        </div>
        <div className="text-sm">
          {posting.status === "queued" || posting.status === "checking" ? (
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              <LoaderCircle
                className="size-4 animate-spin"
                aria-hidden="true"
              />
              {posting.status === "checking" ? "Checking" : "Waiting"}
            </span>
          ) : posting.status === "refused" || posting.status === "failed" ? (
            <span className="text-muted-foreground">Not checked</span>
          ) : (
            <StatusLabel status={posting.status as Status} />
          )}
        </div>
      </div>
      {posting.note && (
        <p className="text-sm text-muted-foreground">{posting.note}</p>
      )}
      {findings.length > 0 && (
        <ul className="space-y-2">
          {findings.map((finding) => (
            <li key={finding.rule} className="flex gap-2 text-sm">
              <VerdictIcon
                verdict={finding.verdict}
                className="mt-0.5 size-4"
              />
              <span>
                <span className="font-medium">{ruleName(finding.rule)}.</span>{" "}
                <span className="text-muted-foreground">{finding.message}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

/** The free sample audit: the first few open Ontario postings on a careers page, findings only. A taste of the
 * paid audit, which checks every posting and writes the fixes. */
export function SampleAudit() {
  const [url, setUrl] = useState("")
  const [sample, setSample] = useState<SampleOut | null>(null)
  const [reading, setReading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quota, setQuota] = useState(false)

  const update = (posting: SamplePosting) =>
    setSample((current) =>
      current
        ? {
            ...current,
            postings: current.postings.map((p) =>
              p.index === posting.index ? posting : p,
            ),
          }
        : current,
    )

  const run = async () => {
    setReading(true)
    setError(null)
    setQuota(false)
    setSample(null)
    let found: SampleOut
    try {
      found = (await AuditsService.startSample({ body: { url } })).data
    } catch (err) {
      track("sample-audit-not-run", { reason: reason(err) })
      setQuota(reason(err) === "quota")
      setError(
        apiMessage(err as Error, "We couldn't read that page. Try again."),
      )
      return
    } finally {
      setReading(false)
    }
    setSample(found)
    track("sample-audit", {
      postings: found.postings.length,
      source: found.source,
    })
    for (const posting of found.postings) {
      update({ ...posting, status: "checking" })
      try {
        const { data } = await AuditsService.checkSamplePosting({
          path: { sample_id: found.sample_id, index: posting.index },
        })
        update(data)
      } catch (err) {
        const why = reason(err)
        update({
          ...posting,
          status: "failed",
          note: apiMessage(err as Error, "We couldn't check this posting."),
        })
        if (why === "quota" || why === "paused") {
          setQuota(why === "quota")
          setError(
            apiMessage(
              err as Error,
              "Free checks are paused. Try again tomorrow.",
            ),
          )
          break
        }
      }
    }
  }

  const done = sample?.postings.every(
    (p) => !["queued", "checking"].includes(p.status),
  )
  const rest = sample ? sample.in_ontario - sample.postings.length : 0

  return (
    <section id="audit" className="scroll-mt-16">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 sm:py-28 lg:grid-cols-12 lg:gap-8">
        <div className="lg:col-span-5">
          <Kicker>Careers page audit</Kicker>
          <Heading className="mt-5">How do your open postings do?</Heading>
          <p className="mt-6 text-muted-foreground">
            Enter your careers page or job board. We check the first three open
            Ontario postings on it and show what each one misses. Free once a
            week, no sign-up.
          </p>
          <p className="mt-4 text-muted-foreground">
            On a paid plan, an audit checks every posting on the board and
            writes the fixes for you to approve.
          </p>
        </div>
        <div className="min-w-0 space-y-6 lg:col-span-6 lg:col-start-7">
          <form
            className="rounded-2xl border bg-card p-5 shadow-sm sm:p-6"
            onSubmit={(event) => {
              event.preventDefault()
              run()
            }}
          >
            <label htmlFor="sample-url" className="text-sm font-medium">
              Careers page or job board
            </label>
            <p className="text-xs text-muted-foreground">
              Greenhouse, Lever and Ashby boards, or a page on your site that
              lists your openings.
            </p>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <Input
                id="sample-url"
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
                loading={reading}
                disabled={!url.trim() || (Boolean(sample) && !done)}
              >
                Check 3 postings free <ArrowRight />
              </LoadingButton>
            </div>
            <p className="mt-4 border-t pt-4 text-xs text-muted-foreground">
              We follow each site's robots.txt and keep nothing from the
              postings. Findings only: no fixes in the free sample.
            </p>
          </form>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>
                {error}
                {quota && (
                  <span>
                    {" "}
                    <a href="#pricing" className="underline underline-offset-4">
                      See the plans
                    </a>{" "}
                    to audit every posting.
                  </span>
                )}
              </AlertDescription>
            </Alert>
          )}

          {sample && (
            <div className="rounded-2xl border bg-card shadow-sm">
              <div className="border-b px-5 py-4">
                <h3 className="font-semibold">
                  {sample.postings.length
                    ? `The first ${sample.postings.length} of ${sample.in_ontario} open postings for Ontario`
                    : "No open postings for Ontario"}
                </h3>
                <p className="text-sm text-muted-foreground">
                  On {sample.board_name ?? shortAddress(sample.url)}
                  {sample.outside_ontario > 0 &&
                    `, plus ${sample.outside_ontario} for work outside Ontario`}
                  .
                </p>
              </div>
              {sample.postings.length > 0 && (
                <ul className="divide-y">
                  {sample.postings.map((posting) => (
                    <Result key={posting.index} posting={posting} />
                  ))}
                </ul>
              )}
              {done && sample.postings.length > 0 && (
                <div className="flex flex-col gap-3 border-t px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-sm text-muted-foreground">
                    {rest > 0
                      ? `${rest} more ${rest === 1 ? "posting wasn't" : "postings weren't"} checked. A paid audit checks them all, with fixes.`
                      : "A paid audit adds the fixes for each posting."}
                  </p>
                  <Button asChild>
                    {isLoggedIn() ? (
                      <Link to="/audits">Audit them all</Link>
                    ) : (
                      <a href="#pricing">See the plans</a>
                    )}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
