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
  type WorkspacePublic,
  type WorkspaceUpdate,
} from "@/client"
import { FREE_ACCOUNT_CHECKS } from "@/components/Billing/UsageMeter"
import {
  ProfileNote,
  profileAnswers,
  SaveToProfile,
} from "@/components/Profile/ProfileNote"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { LoadingButton } from "@/components/ui/loading-button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { isLoggedIn } from "@/hooks/useAuth"
import { useStickyEnd } from "@/hooks/useStickyEnd"
import { track } from "@/lib/analytics"
import { cn } from "@/lib/utils"
import { ApplicationForm, FORM_NOTES } from "./ApplicationForm"
import { Findings } from "./Findings"
import { type Choices, defaultChoices, Fixes } from "./Fixes"
import { PostingEditor } from "./PostingEditor"
import { LINK_REFUSALS, PostingLink } from "./PostingLink"
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

type Input = "text" | "link"

/** One side of the results: whichever is shorter holds its end in view while the other is read. */
function ResultColumn({ children }: { children: ReactNode }) {
  const ref = useStickyEnd<HTMLDivElement>()
  return (
    <div ref={ref} className="min-w-0 lg:sticky">
      {children}
    </div>
  )
}

/** More checks, for a refusal on the public page: a free account for visitors, the plans for everyone. */
function SeePlans() {
  if (isLoggedIn()) {
    return (
      <span>
        {" "}
        Need more checks?{" "}
        <a href="#pricing" className="underline underline-offset-4">
          See the plans
        </a>
        .
      </span>
    )
  }
  return (
    <span>
      {" "}
      Want more?{" "}
      <Link to="/signup" className="underline underline-offset-4">
        Create a free account
      </Link>{" "}
      for {FREE_ACCOUNT_CHECKS} checks a month, or{" "}
      <Link to="/login" className="underline underline-offset-4">
        log in
      </Link>
      .
    </span>
  )
}

/** The check. On the public page (`hero`) the paste form sits beside `intro` and results open below it in a
 * full-width band; in the signed-in app (`app`) everything stacks inside the page. The posting is pasted or
 * given as a link the server reads; its application form, when added, is checked right after it as one more
 * check. A signed-in customer's check counts against their plan and starts from their company `profile` (the
 * API reads the sign-in), which on Agency is the picked `client`'s; `editProfile` renders the link to change
 * it. `onChecked` runs after each check and after fixes are applied. `opened` shows a check made elsewhere (a
 * posting from a careers page audit) without the paste form, and writes its fixes as it opens. `initialUrl`
 * opens the form on a posting's link, ready to check (a posting from a report). `hint` sits under the check
 * button (the public page's link to its sample result). */
export function Checker({
  intro,
  layout = "hero",
  note = FREE_NOTE,
  onChecked,
  profile,
  editProfile,
  client = false,
  opened,
  initialUrl,
  hint,
}: {
  intro?: ReactNode
  layout?: "hero" | "app"
  note?: ReactNode
  onChecked?: () => void
  profile?: WorkspacePublic
  editProfile?: (label: string) => ReactNode
  client?: boolean
  opened?: CheckOut
  initialUrl?: string
  hint?: ReactNode
}) {
  const hero = layout === "hero"
  const [input, setInput] = useState<Input>(initialUrl ? "link" : "text")
  const [text, setText] = useState("")
  const [url, setUrl] = useState(initialUrl ?? "")
  const [form, setForm] = useState("")
  const [checkedForm, setCheckedForm] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [formRefusal, setFormRefusal] = useState<string | null>(null)
  const [check, setCheck] = useState<CheckOut | null>(opened ?? null)
  const [choices, setChoices] = useState<Choices>(() =>
    opened?.refinement ? defaultChoices(opened.refinement) : {},
  )
  const [final, setFinal] = useState<FinalOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refusal, setRefusal] = useState<string | null>(null)
  const [toSave, setToSave] = useState<WorkspaceUpdate>({})
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

  const checkForm = useMutation({
    mutationFn: async ({
      checkId,
      questions,
    }: {
      checkId: string
      questions: string
    }) =>
      (
        await ChecksService.checkForm({
          body: { check_id: checkId, form: questions },
        })
      ).data,
    onMutate: () => {
      setFormError(null)
      setFormRefusal(null)
    },
    onSuccess: (data, { questions }) => {
      track("check-form", { status: data.report.status })
      setCheckedForm(questions)
      show(data)
      onChecked?.()
    },
    onError: (err) => {
      setFormRefusal(refusalReason(err))
      setFormError(errorMessage(err))
    },
  })

  const inspect = useMutation({
    mutationFn: async () =>
      (
        await ChecksService.inspectPosting({
          body:
            input === "link"
              ? { url: url.trim(), workspace_id: profile?.id }
              : { text, workspace_id: profile?.id },
        })
      ).data,
    onMutate: () => {
      setError(null)
      setRefusal(null)
      setFormError(null)
      setCheckedForm(null)
      setCheck(null)
      setFinal(null)
      setToSave({})
    },
    onSuccess: (data) => {
      track("check", { status: data.report.status, input })
      show(data)
      onChecked?.()
      if (input === "link") setText(data.text.slice(0, MAX_CHARS))
      if (data.report.status === "not_applicable") return
      // The form goes right after the posting, before the fixes, so the fixes' report covers it too.
      const fixes = () => refine.mutate(data.check_id)
      if (form.trim())
        checkForm.mutate(
          { checkId: data.check_id, questions: form },
          { onSettled: fixes },
        )
      else fixes()
    },
    onError: (err) => {
      const reason = refusalReason(err)
      track("check-not-run", { reason })
      setRefusal(reason)
      fail(err)
      if (input === "link" && LINK_REFUSALS.has(reason)) setInput("text") // the paste box is the way on
    },
  })

  const answer = useMutation({
    mutationFn: async (answers: Answers) =>
      (
        await ChecksService.answerQuestions({
          body: { check_id: check!.check_id, answers },
        })
      ).data,
    onSuccess: (data, answers) => {
      show(data)
      setToSave((saved) => ({ ...saved, ...profileAnswers(answers) }))
    },
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

  const refineOpened = useRef(false)
  useEffect(() => {
    if (
      opened &&
      !opened.refinement &&
      opened.report.status !== "not_applicable" &&
      !refineOpened.current
    ) {
      refineOpened.current = true
      refine.mutate(opened.check_id)
    }
  }, [opened, refine.mutate])

  const checkId = check?.check_id
  useEffect(() => {
    if (checkId && !opened)
      results.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [checkId, opened])
  useEffect(() => {
    if (final)
      editor.current?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [final])

  const busy =
    inspect.isPending ||
    refine.isPending ||
    answer.isPending ||
    checkForm.isPending
  const ready = input === "link" ? Boolean(url.trim()) : Boolean(text.trim())
  // A posting already checked can have its form checked on its own (one more check), once per version.
  const formAlone =
    check && check.report.status !== "not_applicable" && form !== checkedForm
      ? () => checkForm.mutate({ checkId: check.check_id, questions: form })
      : undefined

  return (
    <>
      {/* #check is the public page's hero (landing.css gives it the photo); the app's checker isn't */}
      <section
        id={hero ? "check" : undefined}
        data-dock={hero ? undefined : "Check"}
        className={hero ? "scroll-mt-20" : undefined}
        hidden={Boolean(opened)}
      >
        <div
          className={cn(
            hero &&
              "mx-auto grid max-w-6xl gap-6 px-4 pt-6 pb-12 sm:gap-10 sm:px-6 sm:pt-12 sm:pb-16 lg:grid-cols-[1fr_1.1fr] lg:items-center lg:pt-20",
          )}
        >
          {intro}
          {/* On a phone the hero's check button moves up under the posting, so the first check fits on the first
              screen; the application form follows it */}
          <div
            className={cn(
              "min-w-0 rounded-2xl border bg-card p-5 sm:p-6",
              hero
                ? "glass-card flex flex-col shadow-lg shadow-primary/5"
                : "shadow-sm",
            )}
          >
            <Tabs
              value={input}
              onValueChange={(value) => setInput(value as Input)}
              className="gap-0"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label
                  htmlFor={input === "link" ? "posting-link" : "posting"}
                  className="text-sm font-medium"
                >
                  {input === "link"
                    ? "Link to one job posting"
                    : "Paste one job posting"}
                </label>
                <TabsList className="h-8">
                  <TabsTrigger value="text" className="px-3 text-xs">
                    Paste text
                  </TabsTrigger>
                  <TabsTrigger value="link" className="px-3 text-xs">
                    Link
                  </TabsTrigger>
                </TabsList>
              </div>
              {profile && editProfile && (
                <div className="mt-3">
                  <ProfileNote
                    profile={profile}
                    edit={editProfile}
                    client={client}
                  />
                </div>
              )}
              <TabsContent value="text">
                <p className="text-xs text-muted-foreground">
                  The whole text applicants will read. Paste any linked document
                  too.
                </p>
                <textarea
                  id="posting"
                  value={text}
                  onChange={(event) =>
                    setText(event.target.value.slice(0, MAX_CHARS))
                  }
                  placeholder="Job title, location, duties, requirements, pay…"
                  className={cn(
                    "mt-2 w-full resize-y rounded-lg border bg-background p-3 text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                    hero ? "min-h-28 sm:min-h-72" : "min-h-48",
                  )}
                />
              </TabsContent>
              <TabsContent value="link" className="mt-2">
                <PostingLink
                  value={url}
                  onChange={setUrl}
                  onSubmit={() => !busy && inspect.mutate()}
                  read={
                    check?.url
                      ? { url: check.url, characters: check.text.length }
                      : null
                  }
                />
              </TabsContent>
            </Tabs>
            <ApplicationForm
              className={cn("mt-4", hero && "max-sm:order-3")}
              value={form}
              onChange={setForm}
              note={
                FORM_NOTES[profile ? "plan" : isLoggedIn() ? "check" : "free"]
              }
              onCheck={busy ? undefined : formAlone}
              checking={checkForm.isPending}
              error={
                formError && (
                  <>
                    {formError}
                    {formRefusal === "quota" && hero && <SeePlans />}
                  </>
                )
              }
            />
            <div
              className={cn(
                "mt-3 flex flex-wrap items-center justify-between gap-3",
                hero && "max-sm:order-1",
              )}
            >
              <span
                className={cn(
                  "text-xs text-muted-foreground",
                  hero && !text && "max-sm:hidden",
                )}
              >
                {input === "text" &&
                  `${text.length.toLocaleString()} / ${MAX_CHARS.toLocaleString()} characters`}
              </span>
              <LoadingButton
                size="lg"
                loading={inspect.isPending}
                disabled={!ready || busy}
                onClick={() => inspect.mutate()}
              >
                Check my posting <ArrowRight />
              </LoadingButton>
            </div>
            {hint && <p className="mt-3 text-sm max-sm:order-2">{hint}</p>}
            <p
              className={cn(
                "mt-4 flex items-start gap-2 border-t pt-4 text-xs text-muted-foreground",
                hero && "max-sm:order-4",
              )}
            >
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
          data-dock={hero ? undefined : "Results"}
          className={cn(
            hero ? "landing-panel mb-3 scroll-mt-20" : !opened && "pt-6",
          )}
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
                  {refusal === "quota" && hero && <SeePlans />}
                </AlertDescription>
              </Alert>
            )}
            {inspect.isPending && (
              <p className="text-sm text-muted-foreground">
                {input === "link"
                  ? "Reading the page and checking each rule…"
                  : "Reading your posting and checking each rule…"}
              </p>
            )}
            {checkForm.isPending && (
              <p className="text-sm text-muted-foreground">
                Checking the application form…
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
                {check.workspace_id &&
                  profile &&
                  Object.keys(toSave).length > 0 && (
                    <SaveToProfile
                      key={JSON.stringify(toSave)}
                      workspaceId={check.workspace_id}
                      threshold={profile.headcount_threshold}
                      answers={toSave}
                    />
                  )}
                <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
                  <ResultColumn>
                    <Findings
                      checkId={check.check_id}
                      report={check.report}
                      text={check.text}
                      formText={check.form_text}
                      url={check.url}
                    />
                  </ResultColumn>
                  <ResultColumn>
                    {check.refinement ? (
                      <Fixes
                        checkId={check.check_id}
                        refinement={check.refinement}
                        choices={choices}
                        onChange={setChoices}
                        onApply={() => accept.mutate()}
                        applying={accept.isPending}
                        onPayConfirmed={check.workspace_id ? show : undefined}
                      />
                    ) : (
                      refine.isPending && (
                        <div className="rounded-xl border bg-card p-5 text-sm text-muted-foreground shadow-sm">
                          Writing suggested fixes…
                        </div>
                      )
                    )}
                  </ResultColumn>
                </div>
                {final && (
                  <div
                    ref={editor}
                    data-dock={hero ? undefined : "Your posting"}
                    className={cn(hero && "scroll-mt-20")}
                  >
                    <PostingEditor
                      final={final}
                      archiveLink={(label, postingId) => (
                        <Link
                          to="/archive"
                          search={{ posting: postingId }}
                          className="underline underline-offset-4"
                        >
                          {label}
                        </Link>
                      )}
                    />
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
