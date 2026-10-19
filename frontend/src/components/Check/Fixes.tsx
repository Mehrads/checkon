import type { Decision, Refinement } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { LoadingButton } from "@/components/ui/loading-button"
import { cn } from "@/lib/utils"
import { FeedbackButtons } from "./Feedback"
import { ruleName, WRITER_TEXT } from "./labels"

export type Choices = Record<string, Decision>

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
}

export function Fixes({
  checkId,
  refinement,
  choices,
  onChange,
  onApply,
  applying,
}: FixesProps) {
  const set = (decision: Decision) =>
    onChange({ ...choices, [decision.patch_id]: decision })
  const missingChoice = refinement.patches.some(
    (patch) =>
      (patch.options ?? []).length > 0 &&
      choices[patch.id]?.accept &&
      choices[patch.id]?.option == null,
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Suggested fixes</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {refinement.patches.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No changes needed for the rules we can fix automatically.
          </p>
        )}
        {refinement.patches.map((patch) => {
          const choice = choices[patch.id]
          const options = patch.options ?? []
          return (
            <div key={patch.id} className="rounded-md border p-3">
              <div className="flex items-center gap-3">
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
                <Badge variant="secondary">{WRITER_TEXT[patch.writer]}</Badge>
                {!patch.default && options.length === 0 && (
                  <Badge variant="outline">Suggestion</Badge>
                )}
                <div className="ml-auto">
                  <FeedbackButtons
                    checkId={checkId}
                    kind="patch"
                    target={patch.id}
                  />
                </div>
              </div>
              <div className="mt-3 flex flex-col gap-1 text-sm">
                {patch.before && (
                  <p className="text-destructive line-through">
                    {patch.before}
                  </p>
                )}
                {patch.after && (
                  <p className="whitespace-pre-line text-green-700 dark:text-green-400">
                    {patch.after.trim()}
                  </p>
                )}
                {options.length > 0 && (
                  <div className="mt-2 flex flex-col gap-2">
                    <p className="text-muted-foreground">
                      Pick the range you genuinely expect to pay:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {options.map((option, index) => (
                        <Button
                          key={option}
                          size="sm"
                          variant="outline"
                          className={cn(
                            choice?.option === index &&
                              "border-green-600 text-green-700 dark:text-green-400",
                          )}
                          onClick={() =>
                            set({
                              patch_id: patch.id,
                              accept: true,
                              option: index,
                            })
                          }
                        >
                          {option}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
        {refinement.dropped.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium">Fix these yourself</p>
            {refinement.dropped.map((dropped) => (
              <p
                key={`${dropped.rule}-${dropped.span?.join("-")}`}
                className="text-sm text-muted-foreground"
              >
                <span className="font-medium text-foreground">
                  {ruleName(dropped.rule)}:
                </span>{" "}
                {dropped.guidance}
              </p>
            ))}
          </div>
        )}
        <LoadingButton
          loading={applying}
          disabled={missingChoice}
          onClick={onApply}
          className="self-start"
        >
          Apply selected fixes
        </LoadingButton>
      </CardContent>
    </Card>
  )
}
