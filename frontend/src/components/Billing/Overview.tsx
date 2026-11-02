import {
  ChartColumnBig,
  CircleAlert,
  CircleCheck,
  Gauge,
  type LucideIcon,
} from "lucide-react"
import type { ReactNode } from "react"

import type { BillingOut, PaidCheckPublic } from "@/client"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { usePaidChecks } from "@/hooks/useBilling"
import { cn } from "@/lib/utils"
import { formatDay } from "./UsageMeter"

const WEEKS = 8

/** Where a check stands now: after its fixes, if any were applied. */
function standing(check: PaidCheckPublic): "met" | "open" | "other" {
  const status = check.final_status ?? check.status
  if (status === "compliant") return "met"
  return status === "not_applicable" ? "other" : "open"
}

/** "Latest 38 checks", or "Latest 100 of 240 checks" when the account has more than one page of them. */
function latest(loaded: number, count: number): string {
  return count > loaded
    ? `Latest ${loaded} of ${count} checks`
    : `Latest ${loaded} ${loaded === 1 ? "check" : "checks"}`
}

function Tile({
  label,
  value,
  note,
  icon: Icon,
  accent = false,
  children,
}: {
  label: string
  value: ReactNode
  note: string
  icon: LucideIcon
  accent?: boolean
  children?: ReactNode
}) {
  return (
    // biome-ignore lint/a11y/useSemanticElements: a stat tile, not a set of form fields
    <div
      role="group"
      aria-label={label}
      className={cn(
        "flex min-w-0 flex-col justify-between gap-3 rounded-xl border p-4 shadow-sm",
        accent ? "tile-accent border-transparent" : "bg-card",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p
          className={cn(
            "text-sm",
            accent ? "text-white/90" : "text-muted-foreground",
          )}
        >
          {label}
        </p>
        <span
          className={cn(
            "flex size-7 shrink-0 items-center justify-center rounded-full",
            accent ? "bg-white/15" : "bg-solid/80 text-on-solid",
          )}
        >
          <Icon className="size-4" aria-hidden="true" />
        </span>
      </div>
      <div>
        <p className="text-3xl leading-none font-semibold tracking-tight tabular-nums">
          {value}
        </p>
        <p
          className={cn(
            "mt-2 flex flex-wrap items-center gap-1.5 text-xs",
            accent ? "text-white/90" : "text-muted-foreground",
          )}
        >
          {children}
          {note}
        </p>
      </div>
    </div>
  )
}

/** A share of the checks, in the small chip beside a tile's note. */
function Share({ part, whole }: { part: number; whole: number }) {
  return (
    <span className="rounded-full bg-solid/70 px-1.5 py-0.5 font-medium text-on-solid tabular-nums">
      {whole ? Math.round((part / whole) * 100) : 0}%
    </span>
  )
}

/** Four numbers at a glance: the plan's checks this period, and how the account's latest checks stand. */
export function CheckStats({ billing }: { billing: BillingOut }) {
  const { data, isPending } = usePaidChecks()
  if (isPending) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {[0, 1, 2, 3].map((tile) => (
          <Skeleton key={tile} className="h-32 rounded-xl" />
        ))}
      </div>
    )
  }
  const checks = data?.data ?? []
  const count = data?.count ?? 0
  const met = checks.filter((check) => standing(check) === "met").length
  const open = checks.filter((check) => standing(check) === "open").length
  const included = billing.checks_included
  const used = Math.min(billing.checks_used, included)
  const renews = billing.complimentary
    ? "In the last 30 days"
    : billing.period_end
      ? `${billing.plan === "free" ? "More on" : billing.cancel_at_period_end ? "Ends" : "Renews"} ${formatDay(billing.period_end)}`
      : "This period"
  return (
    <div className="grid grid-cols-2 gap-3">
      <Tile
        accent
        label="Checks used"
        value={used}
        note={`of ${included} this period`}
        icon={Gauge}
      />
      <Tile
        label="Checks left"
        value={included - used}
        note={renews}
        icon={ChartColumnBig}
      />
      <Tile
        label="Meet the rules"
        value={met}
        note={latest(checks.length, count)}
        icon={CircleCheck}
      >
        <Share part={met} whole={checks.length} />
      </Tile>
      <Tile
        label="Need work"
        value={open}
        note={latest(checks.length, count)}
        icon={CircleAlert}
      >
        <Share part={open} whole={checks.length} />
      </Tile>
    </div>
  )
}

type Week = {
  start: Date
  label: string
  met: number
  open: number
  other: number
}

function monday(day: Date): Date {
  const start = new Date(day)
  start.setHours(0, 0, 0, 0)
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7))
  return start
}

function byWeek(checks: PaidCheckPublic[]): Week[] {
  const thisWeek = monday(new Date())
  const weeks = Array.from({ length: WEEKS }, (_, index): Week => {
    const start = new Date(thisWeek)
    start.setDate(start.getDate() - (WEEKS - 1 - index) * 7)
    return {
      start,
      label: start.toLocaleDateString("en-CA", {
        month: "short",
        day: "numeric",
      }),
      met: 0,
      open: 0,
      other: 0,
    }
  })
  for (const check of checks) {
    const start = monday(new Date(check.created_at)).getTime()
    const week = weeks.find((item) => item.start.getTime() === start)
    if (week) week[standing(check)] += 1
  }
  return weeks
}

/** The axis top and its step: whole checks, at most five lines. */
function axis(most: number): { top: number; step: number } {
  const step = Math.max(1, Math.ceil(most / 4))
  return { top: Math.max(step, Math.ceil(most / step) * step), step }
}

function Legend({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={cn("size-2.5 rounded-full", className)} />
      {label}
    </span>
  )
}

function WeekColumn({ week, top }: { week: Week; top: number }) {
  const height = (part: number) => `${(part / top) * 100}%`
  const summary = `Week of ${week.label}: ${week.met} meet the rules, ${week.open} need work`
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          role="img"
          aria-label={summary}
          className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-0.5 rounded-md hover:bg-foreground/5"
        >
          {week.open > 0 && (
            <span
              className="w-full max-w-6 rounded-t-[4px] bg-chart-open"
              style={{ height: height(week.open) }}
            />
          )}
          {week.met > 0 && (
            <span
              className={cn(
                "w-full max-w-6 bg-chart-met",
                week.open === 0 && "rounded-t-[4px]",
              )}
              style={{ height: height(week.met) }}
            />
          )}
        </div>
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={6}>
        <p className="font-medium">Week of {week.label}</p>
        <p className="tabular-nums">{week.met} meet the rules</p>
        <p className="tabular-nums">{week.open} need work</p>
        {week.other > 0 && (
          <p className="tabular-nums">{week.other} the rules don't apply to</p>
        )}
      </TooltipContent>
    </Tooltip>
  )
}

/** Checks per week for the last eight weeks, split by where each stands now. The table below has every row. */
export function ChecksChart() {
  const { data, isPending } = usePaidChecks()
  const weeks = byWeek(data?.data ?? [])
  const most = Math.max(...weeks.map((week) => week.met + week.open))
  const { top, step } = axis(most)
  const ticks = Array.from(
    { length: top / step + 1 },
    (_, index) => top - index * step,
  )
  return (
    <section className="flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
        <div>
          <h2 className="font-display text-lg font-medium">Checks per week</h2>
          <p className="text-xs text-muted-foreground">
            The last {WEEKS} weeks, by where each check stands now
          </p>
        </div>
        <div className="flex gap-3 text-xs text-muted-foreground">
          <Legend className="bg-chart-met" label="Meet the rules" />
          <Legend className="bg-chart-open" label="Need work" />
        </div>
      </div>
      {isPending ? (
        <Skeleton className="min-h-44 flex-1 rounded-lg" />
      ) : !most ? (
        <p className="flex min-h-44 flex-1 items-center justify-center text-sm text-muted-foreground">
          Your checks will show here.
        </p>
      ) : (
        <div className="flex min-h-44 flex-1 flex-col">
          <div className="relative flex-1">
            {ticks.map((tick) => (
              <div
                key={tick}
                className="absolute inset-x-0 flex items-center gap-2 text-[11px] leading-none text-muted-foreground"
                style={{ top: `${((top - tick) / top) * 100}%` }}
              >
                <span className="w-5 -translate-y-1/2 text-right tabular-nums">
                  {tick}
                </span>
                <span className="h-px flex-1 bg-foreground/10" />
              </div>
            ))}
            <div className="absolute inset-y-0 right-0 left-7 flex items-stretch gap-1.5">
              {weeks.map((week) => (
                <WeekColumn key={week.label} week={week} top={top} />
              ))}
            </div>
          </div>
          <div className="mt-1.5 flex gap-1.5 pl-7 text-[11px] text-muted-foreground">
            {weeks.map((week, index) => (
              <span
                key={week.label}
                className={cn(
                  "min-w-0 flex-1 text-center whitespace-nowrap",
                  index % 2 === 1 && "max-sm:invisible",
                )}
              >
                {week.label}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
