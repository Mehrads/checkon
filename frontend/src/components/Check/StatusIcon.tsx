import {
  CircleAlert,
  CircleCheck,
  CircleHelp,
  CircleMinus,
  CircleX,
} from "lucide-react"

import type { Status, Verdict } from "@/client"
import { cn } from "@/lib/utils"

const VERDICT_ICON = {
  pass: {
    icon: CircleCheck,
    className: "text-emerald-600 dark:text-emerald-400",
  },
  fail: { icon: CircleX, className: "text-red-600 dark:text-red-400" },
  warning: {
    icon: CircleAlert,
    className: "text-amber-600 dark:text-amber-400",
  },
  needs_input: {
    icon: CircleHelp,
    className: "text-sky-600 dark:text-sky-400",
  },
  not_applicable: { icon: CircleMinus, className: "text-muted-foreground" },
} satisfies Record<Verdict, unknown>

const STATUS_VERDICT: Record<Status, Verdict> = {
  compliant: "pass",
  not_compliant: "fail",
  needs_input: "needs_input",
  not_applicable: "not_applicable",
}

export function VerdictIcon({
  verdict,
  className,
}: {
  verdict: Verdict
  className?: string
}) {
  const { icon: Icon, className: tone } = VERDICT_ICON[verdict]
  return (
    <Icon
      className={cn("size-5 shrink-0", tone, className)}
      aria-hidden="true"
    />
  )
}

export function StatusIcon({ status }: { status: Status }) {
  return <VerdictIcon verdict={STATUS_VERDICT[status]} className="size-7" />
}

export const STATUS_LABEL: Record<Status, string> = {
  compliant: "Meets the rules",
  not_compliant: "Doesn't meet the rules",
  needs_input: "Needs answers",
  not_applicable: "Rules don't apply",
}

/** A small icon and a few words, for lists of checks. */
export function StatusLabel({ status }: { status: Status }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <VerdictIcon verdict={STATUS_VERDICT[status]} className="size-4" />
      {STATUS_LABEL[status]}
    </span>
  )
}
