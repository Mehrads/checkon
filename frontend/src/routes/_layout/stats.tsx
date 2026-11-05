import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { CircleAlert, CircleCheck, CircleMinus } from "lucide-react"
import { Suspense } from "react"

import { type StatsOut, StatsService, UsersService, type Week } from "@/client"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

const UMAMI_URL = "https://cloud.umami.is"

export const Route = createFileRoute("/_layout/stats")({
  component: Stats,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({ meta: [{ title: "Stats - CheckON" }] }),
})

const count = new Intl.NumberFormat("en-CA", { notation: "compact" })
const usd = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})
const day = (iso: string) =>
  new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString("en-CA", {
    month: "short",
    day: "numeric",
    year: iso.startsWith(String(new Date().getFullYear()))
      ? undefined
      : "numeric",
  })
const seconds = (value: number | null | undefined) =>
  value == null ? "–" : `${value.toFixed(1)} s`

type State = "good" | "warning" | "none"

const STATE = {
  good: {
    icon: CircleCheck,
    className: "text-emerald-600 dark:text-emerald-400",
  },
  warning: {
    icon: CircleAlert,
    className: "text-amber-600 dark:text-amber-400",
  },
  none: { icon: CircleMinus, className: "text-muted-foreground" },
} satisfies Record<State, unknown>

interface TileProps {
  label: string
  value: string
  detail: string
  state: State
  stateLabel: string
  target: string
}

/** One success metric: its value now, the context, and where it stands against the PRD target. */
function Tile({ label, value, detail, state, stateLabel, target }: TileProps) {
  const { icon: Icon, className } = STATE[state]
  return (
    <div className="flex flex-col rounded-xl border bg-card p-5 shadow-sm">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-3xl font-semibold">{value}</p>
      <p className="mt-1 flex-1 text-sm text-muted-foreground">{detail}</p>
      <p className="mt-4 flex items-start gap-1.5 border-t pt-3 text-xs">
        <Icon
          className={cn("mt-px size-4 shrink-0", className)}
          aria-hidden="true"
        />
        <span>
          {stateLabel}
          <span className="text-muted-foreground"> · {target}</span>
        </span>
      </p>
    </div>
  )
}

function checksTile([thisWeek, lastWeek, weekBefore]: Week[]): TileProps {
  const trend = lastWeek.checks - weekBefore.checks
  return {
    label: "Checks this week",
    value: count.format(thisWeek.checks),
    detail: `Last week ${lastWeek.checks}, the week before ${weekBefore.checks}`,
    state: !lastWeek.checks ? "none" : trend > 0 ? "good" : "warning",
    stateLabel: !lastWeek.checks
      ? "Not enough data yet"
      : trend > 0
        ? "Growing"
        : trend === 0
          ? "Flat"
          : "Shrinking",
    target: "Target: steady week-over-week growth",
  }
}

function returningTile({ returning }: StatsOut): TileProps {
  const rate = returning.rate
  return {
    label: "Returning within 30 days",
    value: rate == null ? "–" : `${Math.round(rate * 100)}%`,
    detail: `${returning.returned} of ${returning.cohort} visitors whose first check is 30+ days old came back`,
    state: rate == null ? "none" : rate >= 0.2 ? "good" : "warning",
    stateLabel:
      rate == null
        ? "Not enough data yet"
        : rate >= 0.2
          ? "On target"
          : "Below target",
    target: "Target: 20%+",
  }
}

function requestsTile({ totals }: StatsOut): TileProps {
  const first = totals.first_check ? new Date(totals.first_check) : null
  const weeksLive = first ? (Date.now() - first.getTime()) / 6048e5 : 0
  const met = totals.custom_requests >= 10
  return {
    label: "Custom requests",
    value: count.format(totals.custom_requests),
    detail: `Plus ${totals.contact_messages} contact messages`,
    state: met ? "good" : first && weeksLive > 8 ? "warning" : "none",
    stateLabel: met
      ? "On target"
      : first && weeksLive > 8
        ? "Below target"
        : `Week ${Math.max(1, Math.ceil(weeksLive))} of 8`,
    target: "Target: 10+ in the first 8 weeks",
  }
}

function timingTile({ timing }: StatsOut): TileProps {
  const p95 = timing.fixes_p95 ?? timing.findings_p95
  return {
    label: "Time per check, p95",
    value: seconds(p95),
    detail: `Results ${seconds(timing.findings_p95)}, with fixes ${seconds(timing.fixes_p95)} (p50 ${seconds(timing.fixes_p50)}), over ${timing.checks} checks in 30 days`,
    state: p95 == null ? "none" : p95 <= 15 ? "good" : "warning",
    stateLabel:
      p95 == null
        ? "Not enough data yet"
        : p95 <= 15
          ? "On target"
          : "Too slow",
    target: "Target: under 15 s",
  }
}

const COLUMNS: { label: string; value: (week: Week) => string }[] = [
  { label: "Checks", value: (w) => String(w.checks) },
  { label: "Visitors", value: (w) => String(w.visitors) },
  { label: "New", value: (w) => String(w.new_visitors) },
  { label: "Weekly limit hit", value: (w) => String(w.limit_hits) },
  { label: "Not a posting", value: (w) => String(w.refused) },
  { label: "Fixes applied", value: (w) => String(w.fixes_applied) },
  { label: "Custom requests", value: (w) => String(w.custom_requests) },
  { label: "Contact", value: (w) => String(w.contact_messages) },
  {
    label: "Feedback up / down",
    value: (w) => `${w.feedback_up} / ${w.feedback_down}`,
  },
  { label: "Model spend", value: (w) => usd.format(Number(w.model_spend_usd)) },
  { label: "Account checks", value: (w) => String(w.account_checks) },
]

function WeeklyTable({ weeks }: { weeks: Week[] }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold">By week</h2>
      <p className="text-sm text-muted-foreground">
        Weeks start Monday, Toronto time. Newest first.
      </p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Week of</TableHead>
            {COLUMNS.map((column) => (
              <TableHead key={column.label} className="text-right">
                {column.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {weeks.map((week, index) => (
            <TableRow key={week.start}>
              <TableCell className="font-medium">
                {index === 0 ? "This week" : day(week.start)}
              </TableCell>
              {COLUMNS.map((column) => (
                <TableCell
                  key={column.label}
                  className="text-right tabular-nums"
                >
                  {column.value(week)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </section>
  )
}

function StatsContent() {
  const { data: stats } = useSuspenseQuery({
    queryKey: ["stats"],
    queryFn: async () => (await StatsService.readStats()).data,
  })
  const { totals } = stats
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Tile {...checksTile(stats.weeks)} />
        <Tile {...returningTile(stats)} />
        <Tile {...requestsTile(stats)} />
        <Tile {...timingTile(stats)} />
      </div>
      <WeeklyTable weeks={stats.weeks} />
      <p className="text-sm text-muted-foreground">
        {totals.first_check
          ? `Since the first check on ${day(totals.first_check)}: `
          : "No checks yet. "}
        {totals.checks} checks from {totals.visitors} visitors,{" "}
        {totals.fixes_applied} with fixes applied,{" "}
        {usd.format(Number(totals.model_spend_usd))} in model fees. Signed-in
        accounts: {totals.accounts} with a check, {totals.account_checks}{" "}
        checks, {usd.format(Number(totals.account_model_spend_usd))} in model
        fees.
      </p>
    </>
  )
}

function Stats() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Stats</h1>
        <p className="text-muted-foreground">
          The free check against the PRD's success metrics, and signed-in
          accounts. Visits and where they come from are in{" "}
          <a
            href={UMAMI_URL}
            target="_blank"
            rel="noreferrer"
            className="underline underline-offset-4"
          >
            Umami
          </a>
          .
        </p>
      </div>
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <StatsContent />
      </Suspense>
    </div>
  )
}
