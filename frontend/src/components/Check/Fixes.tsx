import { CircleAlert } from "lucide-react"

import type { CheckOut, Decision, Patch, Refinement } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { LoadingButton } from "@/components/ui/loading-button"
import { cn } from "@/lib/utils"
import { FeedbackButtons } from "./Feedback"
import { ruleName, WRITER_TEXT } from "./labels"
import { PaySuggestion } from "./PaySuggestion"

export type Choices = Record<string, Decision>

const PAY_RULES = ["ON-PAY-01", "ON-PAY-02"]

export function defaultChoices(refinement: Refinement): Choices {
  return Object.fromEntries(
    refinement.patches.map((patch) => [
      patch.id,
      { patch_id: patch.id, accept: patch.default ?? true },
    ]),
  )
}

interface FixesProps {
  checkId: string
  refinement: Refinement
  choices: Choices
  onChange: (choices: Choices) => void
  onApply: () => void
  applying: boolean
  /** A signed-in user's check: offer a pay range suggestion; the check with the confirmed range comes back. */
  onPayConfirmed?: (check: CheckOut) => void
}

function Change({ patch }: { patch: Patch }) {
  return (
    <div className="space-y-1.5 text-sm">
      {patch.before && (
        <p className="rounded-md bg-red-50 px-3 py-1.5 text-red-800 line-through decoration-red-400 dark:bg-red-950/30 dark:text-red-300">
          {patch.before}
        </p>
      )}
      {patch.after && (
        <p className="whitespace-pre-line rounded-md bg-emerald-50 px-3 py-1.5 text-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300">
          {patch.after.trim()}
        </p>
      )}
    </div>
  )
}

/** One change per finding: the user keeps or drops each, and picks a pay range where one is offered. */
export function Fixes({
  checkId,
  refinement,
  choices,
  onChange,
  onApply,
  applying,
  onPayConfirmed,
}: FixesProps) {
  const set = (decision: Decision) =>
    onChange({ ...choices, [decision.patch_id]: decision })
  const accepted = refinement.patches.filter(
    (patch) => choices[patch.id]?.accept,
  )
  const payFix = [...refinement.patches, ...refinement.dropped].some((fix) =>
    PAY_RULES.includes(fix.rule),
  )
  const missingChoice = accepted.some(
    (patch) =>
      (patch.options ?? []).length > 0 && choices[patch.id]?.option == null,
  )

  return (
    <section
      aria-labelledby="fixes"
      className="rounded-xl border bg-card shadow-sm"
    >
      <header className="border-b px-5 py-4">
        <h2 id="fixes" className="font-semibold">
          Suggested fixes
        </h2>
        <p className="text-sm text-muted-foreground">
          Only what the rules require. Everything else stays as you wrote it.
        </p>
      </header>

      <div className="space-y-3 p-5">
        {refinement.patches.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Nothing to fix automatically.
          </p>
        )}
        {refinement.patches.map((patch) => {
          const choice = choices[patch.id]
          const options = patch.options ?? []
          return (
            <div
              key={patch.id}
              className={cn(
                "group space-y-3 rounded-lg border p-4 transition-colors",
                choice?.accept
                  ? "border-primary/40 bg-primary/5"
                  : "opacity-80",
              )}
            >
              <div className="flex flex-wrap items-center gap-2">
                <Checkbox
                  id={patch.id}
                  checked={choice?.accept ?? false}
                  onCheckedChange={(checked) =>
                    set({
                      ...choice,
                      patch_id: patch.id,
                      accept: checked === true,
                    })
                  }
                />
                <label htmlFor={patch.id} className="font-medium">
                  {ruleName(patch.rule)}
                </label>
                <Badge variant="secondary">
                  {patch.confirmed
                    ? "Your confirmed range"
                    : WRITER_TEXT[patch.writer]}
                </Badge>
                {!patch.default && options.length === 0 && (
                  <Badge variant="outline">Optional</Badge>
                )}
                <div className="ml-auto opacity-60 transition-opacity group-hover:opacity-100">
                  <FeedbackButtons
                    checkId={checkId}
                    kind="patch"
                    target={patch.id}
                  />
                </div>
              </div>
              <Change patch={patch} />
              {options.length > 0 && (
                <fieldset className="space-y-2">
                  <legend className="text-sm text-muted-foreground">
                    Pick the range you genuinely expect to pay:
                  </legend>
                  <div className="flex flex-wrap gap-2">
                    {options.map((option, index) => (
                      <button
                        key={option}
                        type="button"
                        aria-pressed={choice?.option === index}
                        onClick={() =>
                          set({
                            patch_id: patch.id,
                            accept: true,
                            option: index,
                          })
                        }
                        className={cn(
                          "rounded-md border px-3 py-1.5 text-sm transition-colors hover:bg-accent",
                          choice?.option === index &&
                            "border-primary bg-primary text-primary-foreground hover:bg-primary/90",
                        )}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </fieldset>
              )}
            </div>
          )
        })}

        {onPayConfirmed && payFix && (
          <PaySuggestion
            key={checkId}
            checkId={checkId}
            confirmed={refinement.patches.some((patch) => patch.confirmed)}
            onConfirmed={onPayConfirmed}
          />
        )}

        {refinement.dropped.length > 0 && (
          <div className="space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
            <p className="flex items-center gap-2 text-sm font-medium">
              <CircleAlert
                className="size-4 text-amber-600"
                aria-hidden="true"
              />
              Fix these yourself
            </p>
            {refinement.dropped
              // Several sentences under one rule share its guidance: show it once.
              .filter(
                (dropped, index, all) =>
                  all.findIndex(
                    (other) =>
                      other.rule === dropped.rule &&
                      other.guidance === dropped.guidance,
                  ) === index,
              )
              .map((dropped) => (
                <p
                  key={`${dropped.rule}-${dropped.span?.join("-")}`}
                  className="text-sm"
                >
                  <span className="font-medium">{ruleName(dropped.rule)}:</span>{" "}
                  {dropped.guidance}
                </p>
              ))}
          </div>
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t px-5 py-4">
        <p className="text-sm text-muted-foreground">
          {missingChoice
            ? "Pick a pay range to apply that fix."
            : `${accepted.length} of ${refinement.patches.length} fixes selected`}
        </p>
        <LoadingButton
          loading={applying}
          disabled={missingChoice}
          onClick={onApply}
        >
          Apply and edit
        </LoadingButton>
      </footer>
    </section>
  )
}
