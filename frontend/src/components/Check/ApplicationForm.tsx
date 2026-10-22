import { ClipboardList, Plus } from "lucide-react"
import { type ReactNode, useState } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { cn } from "@/lib/utils"

export const MAX_FORM_CHARS = 4000

/** What checking the form costs: one more check, which the weekly free check doesn't leave room for. */
export const FORM_NOTES = {
  plan: "Checking the form uses one more check from your plan.",
  check: "Checking the form uses one more check.",
  free: "Checking the form uses a second check. The free check is one a week, so the form needs a plan.",
}

const HELP =
  'One question per line, with its answer choices on the lines after it, each starting with "-". Add "(optional)" to questions applicants can skip.'

/** The posting's application form: the questions applicants answer, pasted or read from the page. It's checked
 * for Canadian experience, the one rule that covers the form, and uses one more check. Closed until opened or
 * filled. `action` sits beside the label, open or closed (the extension's "Read form"), and `notice` under it;
 * `onCheck` checks the form on its own, for a posting already checked. */
export function ApplicationForm({
  value,
  onChange,
  note,
  action,
  notice,
  onCheck,
  checking = false,
  error,
  className,
}: {
  value: string
  onChange: (value: string) => void
  note: ReactNode
  action?: ReactNode
  notice?: ReactNode
  onCheck?: () => void
  checking?: boolean
  error?: ReactNode
  className?: string
}) {
  const [open, setOpen] = useState(false)

  if (!open && !value) {
    return (
      <div className={cn("space-y-1", className)}>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setOpen(true)}
          >
            <Plus />
            Add the application form
          </Button>
          {action}
        </div>
        <p className="text-xs text-muted-foreground">
          {notice ?? "Its questions are checked for Canadian experience too."}
        </p>
      </div>
    )
  }

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label
          htmlFor="application-form"
          className="flex items-center gap-2 text-sm font-medium"
        >
          <ClipboardList
            className="size-4 text-muted-foreground"
            aria-hidden="true"
          />
          Application form
        </label>
        {action}
      </div>
      <p className="text-xs text-muted-foreground">{notice ?? HELP}</p>
      <textarea
        id="application-form"
        value={value}
        onChange={(event) =>
          onChange(event.target.value.slice(0, MAX_FORM_CHARS))
        }
        placeholder={
          "Do you have Canadian work experience? *\n- Yes\n- No\nYears of payroll experience (optional)"
        }
        className="min-h-28 w-full resize-y rounded-lg border bg-background p-3 text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">{note}</span>
        {onCheck && (
          <LoadingButton
            type="button"
            size="sm"
            variant="secondary"
            loading={checking}
            disabled={!value.trim()}
            onClick={onCheck}
          >
            Check the form
          </LoadingButton>
        )}
      </div>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
