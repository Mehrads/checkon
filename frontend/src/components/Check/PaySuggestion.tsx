import { useMutation } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { Check, Coins, ExternalLink, TriangleAlert } from "lucide-react"
import { useState } from "react"

import {
  type CheckOut,
  type MarketRange,
  PayService,
  type PayUnit,
  type Source,
  type Suggestion,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"

// Shared by the website's checker and the extension's side panel.

const PER: Record<PayUnit, string> = {
  hour: "an hour",
  week: "a week",
  month: "a month",
  year: "a year",
}
// A range whose middle is this far from the market median is flagged, as the API flags a saved range.
const FAR_BELOW = 0.8
const FAR_ABOVE = 1.2

function money(value: number): string {
  return Number.isInteger(value)
    ? `$${value.toLocaleString("en-CA")}`
    : `$${value.toLocaleString("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function payText(low: number, high: number, unit: PayUnit): string {
  return `${low === high ? money(low) : `${money(low)}–${money(high)}`} ${PER[unit]}`
}

/** Pay a year, at the job's hours, as the range rule counts it. */
function yearly(amount: number, unit: PayUnit, hours: number): number {
  const times = { hour: hours * 52, week: 52, month: 12, year: 1 }
  return amount * times[unit]
}

function errorMessage(error: Error): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (detail?.message) return detail.message
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
    if (!error.response)
      return "We couldn't reach CheckON. Check your connection and try again."
  }
  return "Something went wrong. Try again."
}

function marketText(market: MarketRange): string {
  const parts = [
    market.low && `low ${money(Number(market.low))}`,
    `median ${money(Number(market.median))}`,
    market.high && `high ${money(Number(market.high))}`,
  ].filter(Boolean)
  return `${parts.join(" · ")} ${PER[market.unit]}`
}

function SourceItem({ source }: { source: Source }) {
  return (
    <li className="space-y-0.5 text-xs">
      <p>
        {source.url ? (
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 font-medium underline underline-offset-2"
          >
            {source.name}
            <ExternalLink className="size-3" aria-hidden="true" />
          </a>
        ) : (
          <span className="font-medium">{source.name}</span>
        )}
        : {source.figures}
      </p>
      <p className="text-muted-foreground">
        {source.date}
        {source.licence && (
          <>
            {". "}
            {source.licence_url ? (
              <a
                href={source.licence_url}
                target="_blank"
                rel="noreferrer"
                className="underline underline-offset-2"
              >
                {source.licence}
              </a>
            ) : (
              source.licence
            )}
          </>
        )}
      </p>
      {source.quote && (
        <p className="text-muted-foreground italic">“{source.quote}”</p>
      )}
    </li>
  )
}

/** "Suggest a pay range" for a signed-in user's check whose posting has no pay, or a range that is too wide: a
 * range already within the yearly limit, the market range beside it and every source. The user confirms or
 * edits it; only then is it saved for the job title and written into the fixes (`onConfirmed`). */
export function PaySuggestion({
  checkId,
  confirmed,
  onConfirmed,
}: {
  checkId: string
  confirmed: boolean
  onConfirmed: (check: CheckOut) => void
}) {
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null)
  const [low, setLow] = useState("")
  const [high, setHigh] = useState("")
  const [unit, setUnit] = useState<PayUnit>("year")
  const [error, setError] = useState<string | null>(null)
  const [changing, setChanging] = useState(false)

  const ask = useMutation({
    mutationFn: async (noc?: string) =>
      (
        await PayService.suggestPay({
          body: { check_id: checkId, noc_code: noc ?? null },
        })
      ).data,
    onMutate: () => setError(null),
    onSuccess: (data) => {
      setSuggestion(data)
      const start = data.suggested ?? data.band
      setLow(start?.min ?? "")
      setHigh(start?.max ?? "")
      setUnit(start?.unit ?? data.market?.unit ?? "year")
    },
    onError: (err) => setError(errorMessage(err)),
  })

  const confirm = useMutation({
    mutationFn: async () =>
      (
        await PayService.confirmPay({
          body: {
            check_id: checkId,
            min: low,
            max: high,
            unit,
            noc_code: suggestion?.occupation?.code ?? null,
          },
        })
      ).data,
    onMutate: () => setError(null),
    onSuccess: (data) => {
      setChanging(false)
      onConfirmed(data)
    },
    onError: (err) => setError(errorMessage(err)),
  })

  if (confirmed && !changing)
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-dashed p-4 text-sm">
        <p className="flex items-center gap-2">
          <Check className="size-4 text-primary" aria-hidden="true" />
          Your pay range is in the fixes, and saved for this job title.
        </p>
        <Button variant="outline" size="sm" onClick={() => setChanging(true)}>
          Change it
        </Button>
      </div>
    )

  const min = Number(low)
  const max = Number(high)
  const valid = low !== "" && high !== "" && min > 0 && max >= min
  const hours = Number(suggestion?.hours_per_week ?? 40)
  const limit = Number(suggestion?.max_annual_width ?? 50000)
  const width = valid ? yearly(max - min, unit, hours) : 0
  const market = suggestion?.market
  const median = market ? yearly(Number(market.median), market.unit, hours) : 0
  const middle = valid ? yearly((min + max) / 2, unit, hours) : 0
  const far =
    valid && market
      ? middle < median * FAR_BELOW
        ? "below"
        : middle > median * FAR_ABOVE
          ? "above"
          : null
      : null

  return (
    <div className="space-y-4 rounded-lg border border-dashed p-4 text-sm">
      <div className="flex items-start gap-2">
        <Coins
          className="mt-0.5 size-4 shrink-0 text-primary"
          aria-hidden="true"
        />
        <div className="space-y-1">
          <p className="font-medium">Not sure what range to post?</p>
          <p className="text-muted-foreground">
            We suggest one from Job Bank wages and current postings, with every
            source. Nothing goes into your posting until you confirm it.
          </p>
        </div>
      </div>

      {!suggestion && (
        <LoadingButton
          variant="outline"
          loading={ask.isPending}
          onClick={() => ask.mutate(undefined)}
        >
          Suggest a pay range
        </LoadingButton>
      )}
      {ask.isPending && (
        <p className="text-muted-foreground">
          Looking up Job Bank wages and current postings…
        </p>
      )}

      {suggestion?.status === "pick_occupation" && !ask.isPending && (
        <fieldset className="space-y-2">
          <legend className="font-medium">
            Which occupation fits this job best?
          </legend>
          <div className="flex flex-wrap gap-2">
            {(suggestion.alternatives ?? []).map((occupation) => (
              <Button
                key={occupation.code}
                variant="outline"
                size="sm"
                onClick={() => ask.mutate(occupation.code)}
              >
                {occupation.title} (NOC {occupation.code})
              </Button>
            ))}
          </div>
        </fieldset>
      )}

      {suggestion?.status === "suggested" && !ask.isPending && (
        <div className="space-y-4">
          <div className="space-y-1">
            <p className="flex flex-wrap items-center gap-2 font-medium">
              {suggestion.band
                ? "Your saved range"
                : suggestion.suggested
                  ? "Suggested range"
                  : "Your range"}
              <Badge variant="outline">Suggestion</Badge>
            </p>
            {suggestion.occupation && (
              <p className="text-xs text-muted-foreground">
                Matched to {suggestion.occupation.title} (NOC{" "}
                {suggestion.occupation.code}), {suggestion.region} region.
                {(suggestion.alternatives ?? []).map((other) => (
                  <span key={other.code}>
                    {" "}
                    Not right?{" "}
                    <button
                      type="button"
                      className="underline underline-offset-2"
                      onClick={() => ask.mutate(other.code)}
                    >
                      Use {other.title}
                    </button>
                  </span>
                ))}
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor={`${checkId}-low`}>
              Lowest pay
            </label>
            <Input
              id={`${checkId}-low`}
              type="number"
              min={0}
              step="any"
              value={low}
              onChange={(event) => setLow(event.target.value)}
              className="w-28"
            />
            <span>to</span>
            <label className="sr-only" htmlFor={`${checkId}-high`}>
              Highest pay
            </label>
            <Input
              id={`${checkId}-high`}
              type="number"
              min={0}
              step="any"
              value={high}
              onChange={(event) => setHigh(event.target.value)}
              className="w-28"
            />
            <label className="sr-only" htmlFor={`${checkId}-unit`}>
              Pay period
            </label>
            <select
              id={`${checkId}-unit`}
              value={unit}
              onChange={(event) => setUnit(event.target.value as PayUnit)}
              className="h-9 rounded-md border border-input bg-transparent px-2 text-sm shadow-xs dark:bg-input/30"
            >
              {(Object.keys(PER) as PayUnit[]).map((option) => (
                <option key={option} value={option}>
                  {PER[option]}
                </option>
              ))}
            </select>
          </div>

          {market && (
            <p>
              <span className="font-medium">Market:</span> {marketText(market)}{" "}
              <span className="text-muted-foreground">
                ({market.basis === "job_bank" ? "Job Bank" : "current postings"}
                )
              </span>
            </p>
          )}

          {suggestion.flag && suggestion.band && (
            <p className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
              <TriangleAlert
                className="mt-0.5 size-4 shrink-0"
                aria-hidden="true"
              />
              The range you saved for this job,{" "}
              {payText(
                Number(suggestion.band.min),
                Number(suggestion.band.max),
                suggestion.band.unit,
              )}
              , is well {suggestion.flag === "below_market" ? "below" : "above"}{" "}
              the market median.
            </p>
          )}
          {valid && width > limit && (
            <p className="flex items-start gap-2 text-destructive">
              <TriangleAlert
                className="mt-0.5 size-4 shrink-0"
                aria-hidden="true"
              />
              This range is {money(Math.round(width))} a year wide. Keep it
              within {money(limit)} a year.
            </p>
          )}
          {far && !suggestion.flag && width <= limit && (
            <p className="flex items-start gap-2 text-amber-800 dark:text-amber-300">
              <TriangleAlert
                className="mt-0.5 size-4 shrink-0"
                aria-hidden="true"
              />
              This range is well {far} the market median. Post what you
              genuinely expect to pay.
            </p>
          )}

          {(suggestion.sources ?? []).length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-xs font-medium">
                Sources ({suggestion.sources?.length})
              </summary>
              <ul className="mt-2 space-y-3">
                {(suggestion.sources ?? []).map((source) => (
                  <SourceItem
                    key={`${source.kind}-${source.url}-${source.figures}`}
                    source={source}
                  />
                ))}
              </ul>
            </details>
          )}
          {(suggestion.notes ?? []).map((note) => (
            <p key={note} className="text-xs text-muted-foreground">
              {note}
            </p>
          ))}

          <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-3">
            <p className="max-w-sm text-xs text-muted-foreground">
              Market figures are suggestions. Post only a range you genuinely
              expect to pay; we'll save it for this job title.
            </p>
            <LoadingButton
              loading={confirm.isPending}
              disabled={!valid || width > limit}
              onClick={() => confirm.mutate()}
            >
              Use this range
            </LoadingButton>
          </div>
        </div>
      )}

      {error && <p className="text-destructive">{error}</p>}
    </div>
  )
}
