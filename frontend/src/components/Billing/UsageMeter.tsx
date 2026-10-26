import type { BillingOut } from "@/client"
import { cn } from "@/lib/utils"

export const PLAN_PRICE = { starter: "$79", agency: "$249" } as const
export const FREE_ACCOUNT_CHECKS = 5 // every 30 days (PLAN_CHECKS_FREE on the server)

export function formatDay(value: string): string {
  return new Date(value).toLocaleDateString("en-CA", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

/** "12 of 50 checks this period", a bar, and the extra checks past the plan. Shared with the extension,
 * which uses the compact size; the account page shows the count large. */
export function UsageMeter({
  billing,
  className,
  size = "sm",
}: {
  billing: BillingOut
  className?: string
  size?: "sm" | "lg"
}) {
  const included = billing.checks_included
  const used = Math.min(billing.checks_used, included)
  const share = included ? Math.round((used / included) * 100) : 0
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-sm">
        {size === "lg" ? (
          <p className="flex items-baseline gap-2">
            <span className="font-display text-4xl leading-none font-medium tabular-nums">
              {used}
            </span>
            <span className="text-muted-foreground">
              of <span className="tabular-nums">{included}</span> checks this
              period
            </span>
          </p>
        ) : (
          <p>
            <span className="font-semibold tabular-nums">{used}</span> of{" "}
            <span className="tabular-nums">{included}</span> checks this period
          </p>
        )}
        {billing.complimentary ? (
          <p className="text-muted-foreground">In the last 30 days</p>
        ) : (
          billing.period_end && (
            <p className="text-muted-foreground">
              {billing.plan === "free"
                ? "More checks on"
                : billing.cancel_at_period_end
                  ? "Ends"
                  : "Renews"}{" "}
              {formatDay(billing.period_end)}
            </p>
          )
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
