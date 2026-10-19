import { useMutation } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { AxiosError } from "axios"
import { useState } from "react"

import {
  type Answers,
  type CheckOut,
  ChecksService,
  type FinalOut,
} from "@/client"
import { LooksWrong } from "@/components/Check/Feedback"
import { FinalText } from "@/components/Check/FinalText"
import { Findings } from "@/components/Check/Findings"
import { type Choices, defaultChoices, Fixes } from "@/components/Check/Fixes"
import { STATUS_TEXT } from "@/components/Check/labels"
import { Questions } from "@/components/Check/Questions"
import { RequestForm, ResearchQuestionCard } from "@/components/Check/Research"
import { Appearance } from "@/components/Common/Appearance"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { LoadingButton } from "@/components/ui/loading-button"
import { useTurnstile } from "@/hooks/useTurnstile"
import { cn } from "@/lib/utils"

const MAX_CHARS = 8000
const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY as
  | string
  | undefined

export const Route = createFileRoute("/check")({
  component: CheckPage,
  head: () => ({
    meta: [{ title: "Check a job posting - Ontario Job Posting Checker" }],
  }),
})

function errorMessage(error: Error): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (detail?.message) return detail.message
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  }
  return "Something went wrong. Try again."
}

const HEADCOUNT_OPTIONS = [
  { label: "Yes", value: true },
  { label: "No", value: false },
  { label: "Not sure", value: null },
] as const

function CheckPage() {
  const [text, setText] = useState("")
  const [headcount, setHeadcount] = useState<boolean | null>(true)
  const [check, setCheck] = useState<CheckOut | null>(null)
  const [choices, setChoices] = useState<Choices>({})
  const [final, setFinal] = useState<FinalOut | null>(null)
  const [error, setError] = useState<string | null>(null)

  const show = (data: CheckOut) => {
    setCheck(data)
    setFinal(null)
    if (data.refinement) setChoices(defaultChoices(data.refinement))
  }
  const fail = (err: Error) => setError(errorMessage(err))
  const turnstile = useTurnstile(TURNSTILE_SITE_KEY)

  const refine = useMutation({
    mutationFn: async (checkId: string) =>
      (await ChecksService.refinePosting({ body: { check_id: checkId } })).data,
    onSuccess: show,
    onError: fail,
  })

  const inspect = useMutation({
    mutationFn: async () =>
      (
        await ChecksService.inspectPosting({
          body: {
            text,
            meets_headcount_threshold: headcount,
            turnstile_token: turnstile.token,
          },
        })
      ).data,
    onSettled: () => turnstile.reset(), // each token is good for one check
    onMutate: () => {
      setError(null)
      setCheck(null)
      setFinal(null)
    },
    onSuccess: (data) => {
      show(data)
      if (data.report.status !== "not_applicable") refine.mutate(data.check_id)
    },
    onError: fail,
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
    onSuccess: setFinal,
    onError: fail,
  })

  const busy = inspect.isPending || refine.isPending || answer.isPending

  return (
    <div className="min-h-svh">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <span className="font-semibold">Ontario Job Posting Checker</span>
        <Appearance />
      </header>
      <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold">
            Check your job posting before you publish
          </h1>
          <p className="text-muted-foreground">
            Paste one posting. We check it against Ontario's 2026 job posting
            rules and suggest a rewrite that fixes what's missing.
          </p>
        </div>

        <Card>
          <CardContent className="flex flex-col gap-4">
            <textarea
              value={text}
              onChange={(event) =>
                setText(event.target.value.slice(0, MAX_CHARS))
              }
              placeholder="Paste the job posting here"
              className="min-h-64 w-full rounded-md border bg-transparent p-3 text-sm"
              aria-label="Job posting"
            />
            <p className="text-right text-xs text-muted-foreground">
              {text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}{" "}
              characters
            </p>
            <div className="flex flex-col gap-2">
              <p className="text-sm">
                Does your company have 25 or more employees in Ontario?
              </p>
              <div className="flex gap-2">
                {HEADCOUNT_OPTIONS.map((option) => (
                  <Button
                    key={option.label}
                    size="sm"
                    variant="outline"
                    className={cn(
                      headcount === option.value && "border-primary bg-accent",
                    )}
                    onClick={() => setHeadcount(option.value)}
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
            </div>
            <LoadingButton
              loading={inspect.isPending}
              disabled={
                !text.trim() || busy || (turnstile.enabled && !turnstile.token)
              }
              onClick={() => inspect.mutate()}
              className="self-start"
            >
              Check posting
            </LoadingButton>
            <div ref={turnstile.ref} />
            {turnstile.failed && (
              <p className="text-sm text-destructive">
                We couldn't load the check that confirms you're a person. Reload
                the page and try again.
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              One free check per week. We don't keep your posting unless you
              choose to share it with us.
            </p>
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive">
            <AlertTitle>We couldn't finish the check</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {check && (
          <>
            <Alert>
              <AlertTitle>{STATUS_TEXT[check.report.status]}</AlertTitle>
              {check.report.message && (
                <AlertDescription>{check.report.message}</AlertDescription>
              )}
            </Alert>
            <LooksWrong key={check.check_id} checkId={check.check_id} />
            <Questions
              questions={check.questions}
              pending={answer.isPending}
              onAnswer={(answers) => answer.mutate(answers)}
            />
            <Findings
              checkId={check.check_id}
              report={check.report}
              text={check.text}
            />
            {refine.isPending && (
              <p className="text-sm text-muted-foreground">
                Writing suggested fixes…
              </p>
            )}
            {check.refinement && (
              <Fixes
                checkId={check.check_id}
                refinement={check.refinement}
                choices={choices}
                onChange={setChoices}
                onApply={() => accept.mutate()}
                applying={accept.isPending}
              />
            )}
            {final && <FinalText final={final} />}
            <ResearchQuestionCard
              key={`research-${check.check_id}`}
              checkId={check.check_id}
              question={check.research_question}
            />
            <RequestForm
              key={`request-${check.check_id}`}
              checkId={check.check_id}
            />
          </>
        )}

        <p className="text-xs text-muted-foreground">
          This check is not legal advice. It covers Ontario's rules for public
          job postings that took effect on January 1, 2026.
        </p>
      </main>
    </div>
  )
}
