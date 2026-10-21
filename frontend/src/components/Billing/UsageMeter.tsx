import type { BillingOut } from "@/client"
import { cn } from "@/lib/utils"

export const PLAN_PRICE = { starter: "$79", agency: "$249" } as const

export function formatDay(value: string): string {
  return new Date(value).toLocaleDateString("en-CA", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

/** "12 of 50 checks this period", a bar, and the extra checks past the plan. Shared with the extension. */
export function UsageMeter({
  billing,
  className,
}: {
  billing: BillingOut
  className?: string
}) {
  const included = billing.checks_included
  const used = Math.min(billing.checks_used, included)
  const share = included ? Math.round((used / included) * 100) : 0
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-sm">
        <p>
          <span className="font-semibold tabular-nums">{used}</span> of{" "}
          <span className="tabular-nums">{included}</span> checks this period
        </p>
        {billing.period_end && (
          <p className="text-muted-foreground">
            {billing.cancel_at_period_end ? "Ends" : "Renews"}{" "}
            {formatDay(billing.period_end)}
          </p>
        )}
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-label="Checks used this period"
        aria-valuemin={0}
        aria-valuemax={included}
        aria-valuenow={used}
      >
        <div
          className={cn(
            "h-full rounded-full transition-all",
            billing.extra_checks ? "bg-amber-500" : "bg-primary",
          )}
          style={{ width: `${share}%` }}
        />
      </div>
      {billing.extra_checks > 0 && (
        <p className="text-sm text-muted-foreground">
          Plus <span className="tabular-nums">{billing.extra_checks}</span>{" "}
          extra {billing.extra_checks === 1 ? "check" : "checks"} at $1 each, on
          your next invoice ({billing.extra_checks_max} extra checks at most
          each period).
        </p>
      )}
    </div>
  )
}
