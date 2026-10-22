import { useMutation } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { ArrowRight, ClipboardList, ScanText } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"

import {
  type Answers,
  type CheckOut,
  ChecksService,
  type FinalOut,
  type WorkspaceUpdate,
} from "@/client"
import {
  ApplicationForm,
  FORM_NOTES,
  MAX_FORM_CHARS,
} from "@/components/Check/ApplicationForm"
import { Findings } from "@/components/Check/Findings"
import { type Choices, defaultChoices, Fixes } from "@/components/Check/Fixes"
import { PostingEditor } from "@/components/Check/PostingEditor"
import { LINK_REFUSALS, PostingLink } from "@/components/Check/PostingLink"
import { Questions } from "@/components/Check/Questions"
import { Summary } from "@/components/Check/Summary"
import { Logo } from "@/components/Common/Logo"
import {
  ProfileNote,
  profileAnswers,
  SaveToProfile,
} from "@/components/Profile/ProfileNote"
import { WorkspaceSwitcher } from "@/components/Profile/WorkspaceSwitcher"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useWorkspaces } from "@/hooks/useWorkspace"
import { AccountBar, SignIn, useAccount } from "./Account"
import {
  type PagePosting,
  readFormFromPage,
  readFromPage,
  writeToPage,
} from "./page"

const MAX_CHARS = 8000
const SITE = new URL(import.meta.env.VITE_API_URL ?? "https://checkon.ca")
  .origin

const SOURCE_TEXT = {
  selection: "From the text you selected",
  field: "From the job description on this page",
  page: "From this page",
} as const

const UNREADABLE =
  "CheckON can read a page once you click its icon on that page. Click the CheckON icon in the toolbar, or select the posting and right-click › Check with CheckON. You can also paste it below."

/** Why a check didn't run: the API's reason, or the status code. */
function refusalReason(error: Error): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    return detail?.reason ?? String(error.response?.status ?? "network")
  }
  return "unknown"
}

function errorMessage(error: Error): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (detail?.message) return detail.message
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
    if (!error.response)
      return "We couldn't reach CheckON. Check your connection and try again."
  }
  return "Something went wrong. Try again."
}

/** The check in the browser's side panel: read the posting from the page, check it, write the fixes back.
 * Visitors get the free check; a signed-in customer's checks count against their plan and start from their
 * company profile. */
export function Panel() {
  const account = useAccount()
  const onPlan = Boolean(account.billing?.plan)
  const { workspaces, current, canCreate } = useWorkspaces(onPlan)
  const profile = onPlan ? current : undefined
  const [loggingIn, setLoggingIn] = useState(false)
  const [input, setInput] = useState<"text" | "link">("text")
  const [text, setText] = useState("")
  const [url, setUrl] = useState("")
  const [form, setForm] = useState("")
  const [formNotice, setFormNotice] = useState<string | null>(null)
  const [readingForm, setReadingForm] = useState(false)
  const [checkedForm, setCheckedForm] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [posting, setPosting] = useState<PagePosting | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [reading, setReading] = useState(false)
  const [check, setCheck] = useState<CheckOut | null>(null)
  const [choices, setChoices] = useState<Choices>({})
  const [final, setFinal] = useState<FinalOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [toSave, setToSave] = useState<WorkspaceUpdate>({})
  const results = useRef<HTMLDivElement>(null)

  // Set when "Read form" wasn't allowed on this page: the next icon click reads the form, not the posting.
  const formNext = useRef(false)
  const readFormNow = useRef<() => void>(() => {})

  const read = useCallback(async (fallback = "") => {
    setReading(true)
    setNotice(null)
    try {
      const found = await readFromPage()
      if (found) {
        setText(found.text.slice(0, MAX_CHARS))
        setPosting(found)
      } else if (fallback) {
        setText(fallback.slice(0, MAX_CHARS))
        setPosting(null)
      } else {
        setNotice(
          "We didn't find a posting on this page. Select its text, or paste it below.",
        )
      }
    } catch {
      if (fallback) setText(fallback.slice(0, MAX_CHARS))
      setNotice(UNREADABLE)
    } finally {
      setReading(false)
    }
  }, [])

  // The application form is often on another page than the job description: open it, then read it.
  const readForm = async () => {
    setReadingForm(true)
    setFormNotice(null)
    try {
      const found = await readFormFromPage()
      if (found) {
        setForm(found.text.slice(0, MAX_FORM_CHARS))
        setFormNotice(
          found.source === "selection"
            ? "From the text you selected. Check the questions below, then check the form."
            : `Read ${found.questions} ${found.questions === 1 ? "question" : "questions"} from the form on this page. Check them below.`,
        )
      } else {
        setFormNotice(
          "We didn't find a form on this page. Open the application form, or select its questions, then read it again. You can also paste them.",
        )
      }
    } catch {
      formNext.current = true
      setFormNotice(
        "Click the CheckON icon in the toolbar to let CheckON read the form on this page. You can also paste its questions.",
      )
    } finally {
      setReadingForm(false)
    }
  }
  readFormNow.current = readForm

  // Read the page when the panel opens, and again whenever the right-click menu is used.
  useEffect(() => {
    type MenuRequest = { selection?: string; at?: number } | undefined
    const take = (value: unknown) => {
      const request = value as MenuRequest
      if (request?.at && Date.now() - request.at < 60_000) {
        chrome.storage.session.remove("request")
        if (formNext.current && !request.selection) {
          formNext.current = false
          readFormNow.current()
        } else read(request.selection ?? "")
        return true
      }
      return false
    }
    chrome.storage.session.get("request").then(({ request }) => {
      if (!take(request)) read()
    })
    const onChange = (
      changes: Record<string, chrome.storage.StorageChange>,
      area: string,
    ) => {
      if (area === "session" && changes.request?.newValue)
        take(changes.request.newValue)
    }
    chrome.storage.onChanged.addListener(onChange)
    return () => chrome.storage.onChanged.removeListener(onChange)
  }, [read])

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
    onMutate: () => setFormError(null),
    onSuccess: (data, { questions }) => {
      setCheckedForm(questions)
      show(data)
      account.refresh()
    },
    onError: (err) => setFormError(errorMessage(err)),
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
      setFormError(null)
      setCheckedForm(null)
      setCheck(null)
      setFinal(null)
      setToSave({})
    },
    onSuccess: (data) => {
      show(data)
      account.refresh()
      if (input === "link") {
        setText(data.text.slice(0, MAX_CHARS))
        setPosting(null) // read by the server: nothing on this page to write back into
      }
      if (data.report.status === "not_applicable") return
      const fixes = () => refine.mutate(data.check_id)
      if (form.trim())
        checkForm.mutate(
          { checkId: data.check_id, questions: form },
          { onSettled: fixes },
        )
      else fixes()
    },
    onError: (err) => {
      fail(err)
      if (input === "link" && LINK_REFUSALS.has(refusalReason(err)))
        setInput("text")
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
    onSuccess: setFinal,
    onError: fail,
  })

  const checkId = check?.check_id
  useEffect(() => {
    if (checkId) results.current?.scrollIntoView({ behavior: "smooth" })
  }, [checkId])

  const busy =
    inspect.isPending ||
    refine.isPending ||
    answer.isPending ||
    checkForm.isPending
  const ready = input === "link" ? Boolean(url.trim()) : Boolean(text.trim())
  const formAlone =
    check && check.report.status !== "not_applicable" && form !== checkedForm
      ? () => checkForm.mutate({ checkId: check.check_id, questions: form })
      : undefined
  const insert = posting?.editable
    ? (html: string, plain: string) => writeToPage(posting, html, plain)
    : undefined

  return (
    <div className="flex min-h-svh flex-col gap-4 p-4">
      <header className="flex items-center justify-between gap-3">
        <a href={SITE} target="_blank" rel="noreferrer">
          <Logo asLink={false} />
        </a>
        <Button
          variant="outline"
          size="sm"
          onClick={() => read()}
          disabled={reading || busy}
        >
          <ScanText />
          Read page
        </Button>
      </header>

      {loggingIn ? (
        <SignIn
          onSignedIn={(token) => {
            account.signIn(token)
            setLoggingIn(false)
          }}
          onCancel={() => setLoggingIn(false)}
        />
      ) : (
        <AccountBar account={account} onLogIn={() => setLoggingIn(true)} />
      )}

      {profile && canCreate && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Checking for</span>
          <WorkspaceSwitcher
            workspaces={workspaces}
            current={profile}
            className="flex-1 max-w-none"
          />
        </div>
      )}

      <section className="rounded-xl border bg-card p-4 shadow-sm">
        <Tabs
          value={input}
          onValueChange={(value) => setInput(value as "text" | "link")}
          className="gap-0"
        >
          <div className="flex items-center justify-between gap-2">
            <label
              htmlFor={input === "link" ? "posting-link" : "posting"}
              className="text-sm font-medium"
            >
              Job posting
            </label>
            <TabsList className="h-7">
              <TabsTrigger value="text" className="px-2 text-xs">
                Text
              </TabsTrigger>
              <TabsTrigger value="link" className="px-2 text-xs">
                Link
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="text">
            <p className="text-xs text-muted-foreground">
              {reading
                ? "Reading the page…"
                : posting
                  ? posting.source === "selection" && !posting.editable
                    ? "From the text you selected. Copy the result back when you're done."
                    : SOURCE_TEXT[posting.source]
                  : "Paste it, or select it on the page and right-click › Check with CheckON. Paste any linked document too."}
            </p>
            <textarea
              id="posting"
              value={text}
              onChange={(event) => {
                setText(event.target.value.slice(0, MAX_CHARS))
                if (posting?.source === "page") setPosting(null)
              }}
              placeholder="Job title, location, duties, requirements, pay…"
              className="mt-2 min-h-48 w-full resize-y rounded-lg border bg-background p-3 text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
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
        {profile && (
          <div className="mt-2">
            <ProfileNote
              profile={profile}
              client={canCreate}
              edit={(label) => (
                <a
                  href={`${SITE}/profile`}
                  target="_blank"
                  rel="noreferrer"
                  className="underline underline-offset-4"
                >
                  {label}
                </a>
              )}
            />
          </div>
        )}
        <ApplicationForm
          className="mt-4"
          value={form}
          onChange={setForm}
          note={FORM_NOTES[onPlan ? "plan" : "free"]}
          action={
            <LoadingButton
              type="button"
              variant="ghost"
              size="sm"
              loading={readingForm}
              onClick={readForm}
            >
              <ClipboardList />
              Read form
            </LoadingButton>
          }
          notice={formNotice}
          onCheck={busy ? undefined : formAlone}
          checking={checkForm.isPending}
          error={formError}
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-muted-foreground">
            {input === "text" &&
              `${text.length.toLocaleString()} / ${MAX_CHARS.toLocaleString()}`}
          </span>
          <LoadingButton
            loading={inspect.isPending}
            disabled={!ready || busy}
            onClick={() => inspect.mutate()}
          >
            Check this posting <ArrowRight />
          </LoadingButton>
        </div>
        {notice && (
          <p className="mt-3 text-sm text-muted-foreground">{notice}</p>
        )}
      </section>

      {(check || error || busy) && (
        <div ref={results} className="flex flex-col gap-4">
          {error && (
            <Alert variant="destructive">
              <AlertTitle>We couldn't finish the check</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
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
              <Findings
                checkId={check.check_id}
                report={check.report}
                text={check.text}
                formText={check.form_text}
                url={check.url}
              />
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
                  <div className="rounded-xl border bg-card p-4 text-sm text-muted-foreground shadow-sm">
                    Writing suggested fixes…
                  </div>
                )
              )}
              {final && <PostingEditor final={final} onInsert={insert} />}
            </>
          )}
        </div>
      )}

      <footer className="mt-auto border-t pt-3 text-xs text-muted-foreground">
        {account.billing?.plan
          ? `Checks count toward your ${account.billing.plan_name} plan. We keep the date, job title and result, never the posting.`
          : "One free check a week."}{" "}
        Not legal advice.{" "}
        <a
          href={`${SITE}/privacy`}
          target="_blank"
          rel="noreferrer"
          className="underline underline-offset-4"
        >
          Privacy
        </a>
      </footer>
    </div>
  )
}
