import { useMutation } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { AxiosError } from "axios"
import { ArrowRight, ShieldCheck } from "lucide-react"
import { type ReactNode, useEffect, useRef, useState } from "react"

import {
  type Answers,
  type CheckOut,
  ChecksService,
  type FinalOut,
} from "@/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { LoadingButton } from "@/components/ui/loading-button"
import { isLoggedIn } from "@/hooks/useAuth"
import { track } from "@/lib/analytics"
import { cn } from "@/lib/utils"
import { Findings } from "./Findings"
import { type Choices, defaultChoices, Fixes } from "./Fixes"
import { PostingEditor } from "./PostingEditor"
import { Questions } from "./Questions"
import { ResearchQuestionCard } from "./Research"
import { Summary } from "./Summary"

const MAX_CHARS = 8000

function errorMessage(error: Error): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (detail?.message) return detail.message
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  }
  return "Something went wrong. Try again."
}

/** Why a check didn't run, for the analytics event: the API's reason, or the status code. */
function refusalReason(error: Error): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    return detail?.reason ?? String(error.response?.status ?? "network")
  }
  return "unknown"
}

const FREE_NOTE =
  "Free once a week, no sign-up. We don't keep your posting after the check unless you choose to share it with us."

/** The check. On the public page (`hero`) the paste form sits beside `intro` and results open below it in a
 * full-width band; in the signed-in app (`app`) everything stacks inside the page. A signed-in customer's
 * check counts against their plan (the API reads the sign-in), and `onChecked` runs after each check and
 * after fixes are applied. */
export function Checker({
  intro,
  layout = "hero",
  note = FREE_NOTE,
  onChecked,
}: {
  intro?: ReactNode
  layout?: "hero" | "app"
  note?: ReactNode
  onChecked?: () => void
}) {
  const hero = layout === "hero"
  const [text, setText] = useState("")
  const [check, setCheck] = useState<CheckOut | null>(null)
  const [choices, setChoices] = useState<Choices>({})
  const [final, setFinal] = useState<FinalOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refusal, setRefusal] = useState<string | null>(null)
  const results = useRef<HTMLDivElement>(null)
  const editor = useRef<HTMLDivElement>(null)

  const show = (data: CheckOut) => {
    setCheck(data)
    setFinal(null)
    if (data.refinement) setChoices(defaultChoices(data.refinement))
  }
  const fail = (err: Error) => setError(errorMessage(err))

  const refine = useMutation({
    mutationFn: async (checkId: string) =>
      (await ChecksService.refinePosting({ body: { check_id: checkId } })).data,
    onSuccess: show,
    onError: fail,
  })

  const inspect = useMutation({
    mutationFn: async () =>
      (await ChecksService.inspectPosting({ body: { text } })).data,
    onMutate: () => {
      setError(null)
      setRefusal(null)
      setCheck(null)
      setFinal(null)
    },
    onSuccess: (data) => {
      track("check", { status: data.report.status })
      show(data)
      onChecked?.()
      if (data.report.status !== "not_applicable") refine.mutate(data.check_id)
    },
    onError: (err) => {
      const reason = refusalReason(err)
      track("check-not-run", { reason })
      setRefusal(reason)
      fail(err)
    },
  })

  const answer = useMutation({
    mutationFn: async (answers: Answers) =>
      (
        await ChecksService.answerQuestions({
          body: { check_id: check!.check_id, answers },
        })
      ).data,
    onSuccess: show,
    onError: fail,
  })

  const accept = useMutation({
    mutationFn: async () =>
      (
        await ChecksService.acceptPatches({
          body: {
            check_id: check!.check_id,
            decisions: Object.values(choices),
          },
        })
      ).data,
    onSuccess: (data) => {
      track("apply-fixes")
      setFinal(data)
      onChecked?.()
    },
    onError: fail,
  })

  const checkId = check?.check_id
  useEffect(() => {
    if (checkId)
      results.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [checkId])
  useEffect(() => {
    if (final)
      editor.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [final])

  const busy = inspect.isPending || refine.isPending || answer.isPending

  return (
    <>
      <section id="check" className="scroll-mt-20">
        <div
          className={cn(
            hero &&
              "mx-auto grid max-w-6xl gap-10 px-4 pt-12 pb-16 sm:px-6 lg:grid-cols-[1fr_1.1fr] lg:items-center lg:pt-20",
          )}
        >
          {intro}
          <div
            className={cn(
              "min-w-0 rounded-2xl border bg-card p-5 sm:p-6",
              hero ? "shadow-lg shadow-primary/5" : "shadow-sm",
            )}
          >
            <label htmlFor="posting" className="text-sm font-medium">
              Paste one job posting
            </label>
            <textarea
              id="posting"
              value={text}
              onChange={(event) =>
                setText(event.target.value.slice(0, MAX_CHARS))
              }
              placeholder="Job title, location, duties, requirements, pay…"
              className={cn(
                "mt-2 w-full resize-y rounded-lg border bg-background p-3 text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                hero ? "min-h-72" : "min-h-48",
              )}
            />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground">
                {text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}{" "}
                characters
              </span>
              <LoadingButton
                size="lg"
                loading={inspect.isPending}
                disabled={!text.trim() || busy}
                onClick={() => inspect.mutate()}
              >
                Check my posting <ArrowRight />
              </LoadingButton>
            </div>
            <p className="mt-4 flex items-start gap-2 border-t pt-4 text-xs text-muted-foreground">
              <ShieldCheck
                className="mt-px size-4 shrink-0 text-primary"
                aria-hidden="true"
              />
              {note}
            </p>
          </div>
        </div>
      </section>

      {(check || error || busy) && (
        <section
          ref={results}
          className={cn("scroll-mt-20", hero ? "border-t bg-muted/30" : "pt-6")}
        >
          <div
            className={cn(
              "space-y-6",
              hero && "mx-auto max-w-6xl px-4 py-10 sm:px-6",
            )}
          >
            {error && (
              <Alert variant="destructive">
                <AlertTitle>We couldn't finish the check</AlertTitle>
                <AlertDescription>
                  {error}
                  {refusal === "quota" && hero && (
                    <span>
                      Need more checks?{" "}
                      <a
                        href="#pricing"
                        className="underline underline-offset-4"
                      >
                        See the plans
                      </a>
                      {!isLoggedIn() && (
                        <>
                          , or{" "}
                          <Link
                            to="/login"
                            className="underline underline-offset-4"
                          >
                            log in
                          </Link>{" "}
                          if you have one
                        </>
                      )}
                      .
                    </span>
                  )}
                </AlertDescription>
              </Alert>
            )}
            {inspect.isPending && (
              <p className="text-sm text-muted-foreground">
                Reading your posting and checking each rule…
              </p>
            )}
            {check && (
              <>
                <Summary checkId={check.check_id} report={check.report} />
                <Questions
                  questions={check.questions}
                  pending={answer.isPending}
                  onAnswer={(answers) => answer.mutate(answers)}
                />
                <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
                  <Findings
                    checkId={check.check_id}
                    report={check.report}
                    text={check.text}
                  />
                  {check.refinement ? (
                    <Fixes
                      checkId={check.check_id}
                      refinement={check.refinement}
                      choices={choices}
                      onChange={setChoices}
                      onApply={() => accept.mutate()}
                      applying={accept.isPending}
                    />
                  ) : (
                    refine.isPending && (
                      <div className="rounded-xl border bg-card p-5 text-sm text-muted-foreground shadow-sm">
                        Writing suggested fixes…
                      </div>
                    )
                  )}
                </div>
                {final && (
                  <div ref={editor} className="scroll-mt-20">
                    <PostingEditor final={final} />
                  </div>
                )}
                <ResearchQuestionCard
                  key={`research-${check.check_id}`}
                  checkId={check.check_id}
                  question={check.research_question}
                />
              </>
            )}
          </div>
        </section>
      )}
    </>
  )
}
