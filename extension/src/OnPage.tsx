import {
  CircleAlert,
  CircleCheck,
  Eye,
  EyeOff,
  Highlighter,
} from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"

import type { CheckOut, Decision, FinalOut } from "@/client"
import { ruleName } from "@/components/Check/labels"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import type { OverlayItem, OverlayShow, OverlayStatus } from "./overlay"
import type { PagePosting } from "./page"

// The on-page mode from the side panel's end: what to highlight, putting overlay.js into the posting's
// frame, and the decisions made on the page coming back as the panel's fix choices.

const CONTEXT = 80

/** What the check found, as the page shows it: each fix, each "fix this yourself", and the quoted text of
 * any other failing rule. Spans point into check.text. */
export function pageItems(check: CheckOut): OverlayItem[] {
  const text = check.text
  const around = ([start, end]: [number, number]) => ({
    target: text.slice(start, end),
    prefix: text.slice(Math.max(0, start - CONTEXT), start),
    suffix: text.slice(end, end + CONTEXT),
  })
  const message = (rule: string) =>
    check.report.results.find((result) => result.rule === rule)?.message ?? ""
  const patches = check.refinement?.patches ?? []
  const dropped = check.refinement?.dropped ?? []
  const items: OverlayItem[] = patches.map((patch) => ({
    id: patch.id,
    kind: "fix",
    title: ruleName(patch.rule),
    why: message(patch.rule),
    ...around(patch.span),
    fix: patch.after,
    options: patch.options,
    optional: !(patch.default ?? true) && !patch.options?.length,
  }))
  dropped.forEach((fix, i) => {
    if (fix.span)
      items.push({
        id: `d${i}`,
        kind: "note",
        title: ruleName(fix.rule),
        why: fix.guidance,
        ...around(fix.span),
      })
  })
  const covered = new Set([...patches, ...dropped].map((fix) => fix.rule))
  for (const result of check.report.results) {
    if (covered.has(result.rule)) continue
    if (result.verdict !== "fail" && result.verdict !== "warning") continue
    ;(result.evidence ?? []).forEach((span, i) => {
      items.push({
        id: `${result.rule}-${i}`,
        kind: "note",
        title: ruleName(result.rule),
        why: result.message,
        ...around(span),
      })
    })
  }
  return items
}

// One call at a time per panel, so overlay.js goes into a frame once.
let queue: Promise<unknown> = Promise.resolve()
function serial<T>(task: () => Promise<T>): Promise<T> {
  const run = queue.then(task, task)
  queue = run.catch(() => {})
  return run
}

const targetOf = (posting: PagePosting) => ({
  tabId: posting.tabId,
  frameIds: [posting.frameId],
})

function showOnPage(posting: PagePosting, show: OverlayShow) {
  return serial(async () => {
    const target = targetOf(posting)
    const [loaded] = await chrome.scripting.executeScript({
      target,
      func: () => Boolean(window.__checkonOverlay),
    })
    if (!loaded?.result)
      await chrome.scripting.executeScript({ target, files: ["overlay.js"] })
    await chrome.scripting.executeScript({
      target,
      func: (data: OverlayShow) => window.__checkonOverlay?.show(data),
      args: [show],
    })
  })
}

function acceptAllOnPage(posting: PagePosting) {
  return serial(() =>
    chrome.scripting.executeScript({
      target: targetOf(posting),
      func: () => window.__checkonOverlay?.acceptAll(),
    }),
  )
}

function hideOnPage(posting: PagePosting) {
  return serial(() =>
    chrome.scripting.executeScript({
      target: targetOf(posting),
      func: () => window.__checkonOverlay?.hide(),
    }),
  ).catch(() => {})
}

export interface OnPage {
  status: OverlayStatus | null
  /** How many problems the check found to show on the page. */
  count: number
  /** Chrome wouldn't let CheckON show the fixes on this page. */
  failed: boolean
  hidden: boolean
  accepting: boolean
  /** Fixes on the page still waiting for Accept or Skip; notes to fix by hand aren't counted. */
  openFixes: number
  /** Every fix on the page is accepted, copied or skipped, and at least one went in. */
  reviewed: boolean
  show: () => void
  hide: () => void
  acceptAll: () => void
}

/** Shows the check on the page the posting was read from, and turns each Accept or Skip there into a fix
 * choice in the panel. */
export function useOnPage(
  posting: PagePosting | null,
  check: CheckOut | null,
  onDecision: (decision: Decision) => void,
): OnPage {
  const [status, setStatus] = useState<OverlayStatus | null>(null)
  const [failed, setFailed] = useState(false)
  const [hidden, setHidden] = useState(false)
  const [accepting, setAccepting] = useState(false)
  const key = useRef("")
  const shown = useRef<PagePosting | null>(null)
  const decided = useRef<Record<string, string>>({})
  const patches = useRef(new Set<string>())
  const decide = useRef(onDecision)
  decide.current = onDecision

  const count = check ? pageItems(check).length : 0

  useEffect(() => {
    if (!posting || !check || hidden || !pageItems(check).length) {
      if (shown.current) hideOnPage(shown.current)
      shown.current = null
      if (!check) {
        setStatus(null)
        setHidden(false)
      }
      return
    }
    key.current = `${check.check_id}:${Date.now()}`
    // Until the page reports on this version, the last one's counts and Accept all are out of date
    setStatus(null)
    // The panel starts each new version of the check from its default choices: send the page's again.
    decided.current = {}
    patches.current = new Set(
      check.refinement?.patches.map((patch) => patch.id) ?? [],
    )
    shown.current = posting
    setFailed(false)
    showOnPage(posting, {
      key: key.current,
      items: pageItems(check),
      editable: posting.editable,
    }).catch(() => setFailed(true))
  }, [posting, check, hidden])

  useEffect(() => {
    const onMessage = (message: unknown) => {
      const update = message as OverlayStatus
      if (update?.type !== "checkon-overlay" || update.key !== key.current)
        return
      setStatus(update)
      if (!update.visible) setHidden(true)
      for (const [id, { state, option }] of Object.entries(update.states)) {
        const was = decided.current[id]
        decided.current[id] = state
        if (state === was || !patches.current.has(id)) continue
        if (state === "applied" || state === "copied")
          decide.current({ patch_id: id, accept: true, option })
        else if (state === "skipped")
          decide.current({ patch_id: id, accept: false })
      }
    }
    chrome.runtime.onMessage.addListener(onMessage)
    return () => chrome.runtime.onMessage.removeListener(onMessage)
  }, [])

  const acceptAll = useCallback(() => {
    if (!posting) return
    setAccepting(true)
    acceptAllOnPage(posting)
      .catch(() => setFailed(true))
      .finally(() => setAccepting(false))
  }, [posting])

  // A note (fix this yourself) stays highlighted until the employer edits it, so it doesn't hold up the review;
  // a range to pick does, since Accept all can't choose one.
  const fixes = new Set(
    (check ? pageItems(check) : [])
      .filter((item) => item.kind === "fix" && !item.optional)
      .map((item) => item.id),
  )
  const states = Object.entries(status?.states ?? {})
  const openFixes = states.filter(
    ([id, { state }]) => fixes.has(id) && state === "open",
  ).length
  const reviewed =
    !failed &&
    !hidden &&
    openFixes === 0 &&
    states.some(([, { state }]) => state === "applied" || state === "copied")

  return {
    status,
    count,
    failed,
    hidden,
    accepting,
    openFixes,
    reviewed,
    show: () => setHidden(false),
    hide: () => setHidden(true),
    acceptAll,
  }
}

/** The page's progress in the panel: what's fixed, what's left, and Accept all. */
/** What's left once the page is reviewed, said about the posting as it now reads on the page. */
const PAGE_DONE_TEXT: Record<FinalOut["report"]["status"], string> = {
  compliant:
    "Ready to publish: the posting on the page meets Ontario's job posting rules.",
  not_compliant:
    "Some rules are still open. See the rule-by-rule results below and fix those on the page yourself.",
  needs_input:
    "Before you publish, fill in what's marked in brackets on the page:",
  not_applicable: "Ontario's job posting rules don't apply to this posting.",
}

/** "[Pay range: add before publishing]" and the like: what the employer still has to fill in. */
const placeholders = (text: string) => [
  ...new Set(text.match(/\[[^\][\n]{3,80}\]/g) ?? []),
]

/** Once everything on the page is reviewed: whether the posting there is ready, and what's left to fill in. */
function PageDone({ final }: { final: FinalOut }) {
  const status = final.report.status
  const ready = status === "compliant" || status === "not_applicable"
  const Icon = ready ? CircleCheck : CircleAlert
  const left = status === "needs_input" ? placeholders(final.text) : []
  return (
    <div className="flex items-start gap-2 border-t pt-3">
      <Icon
        className={
          ready
            ? "mt-0.5 size-4 shrink-0 text-primary"
            : "mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400"
        }
        aria-hidden="true"
      />
      <div className="space-y-1">
        <p className="font-medium">
          {status === "needs_input" && !left.length
            ? "Before you publish, answer the open questions below."
            : PAGE_DONE_TEXT[status]}
        </p>
        {left.map((mark) => (
          <p key={mark} className="font-mono text-xs">
            {mark}
          </p>
        ))}
      </div>
    </div>
  )
}

export function OnPageStatus({
  onPage,
  final,
}: {
  onPage: OnPage
  /** The posting with the page's decisions applied, once everything there is reviewed. */
  final?: FinalOut | null
}) {
  const { status, failed, hidden, accepting } = onPage
  const states = Object.values(status?.states ?? {}).map(({ state }) => state)
  const count = (state: string) => states.filter((s) => s === state).length
  const open = count("open")
  const missing = count("missing")
  const done = count("applied") + count("copied")
  const editable = status?.editable ?? false

  let line: string
  if (failed)
    line =
      "CheckON can't show the fixes on this page. Use the list below, or click the CheckON icon on the page and check again."
  else if (hidden) line = "Highlights on the page are off."
  else if (!status) line = "Showing the problems on the page…"
  else if (!states.length) line = "Nothing to highlight on the page."
  else
    line = [
      open
        ? `${open} ${open === 1 ? "problem" : "problems"} highlighted on the page`
        : "Everything on the page is reviewed",
      done && `${done} ${editable ? "fixed" : "copied"}`,
      count("skipped") && `${count("skipped")} skipped`,
      missing && `${missing} not found on the page (see the list below)`,
    ]
      .filter(Boolean)
      .join(" · ")

  return (
    <section className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-sm shadow-sm">
      <div className="flex items-start gap-2">
        <Highlighter
          className="mt-0.5 size-4 shrink-0 text-primary"
          aria-hidden="true"
        />
        <p>
          {line}
          {!hidden && status && open > 0 && (
            <span className="text-muted-foreground">
              {editable
                ? ". Click one to accept or skip its fix."
                : ". This page can't be edited: copy each fix from its card."}
            </span>
          )}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {editable && !hidden && onPage.openFixes > 0 && (
          <LoadingButton
            size="sm"
            loading={accepting}
            onClick={onPage.acceptAll}
          >
            Accept all on the page
          </LoadingButton>
        )}
        {hidden ? (
          <Button size="sm" variant="outline" onClick={onPage.show}>
            <Eye />
            Show on the page
          </Button>
        ) : (
          !failed && (
            <Button size="sm" variant="ghost" onClick={onPage.hide}>
              <EyeOff />
              Hide highlights
            </Button>
          )
        )}
      </div>
      {onPage.reviewed && final && <PageDone final={final} />}
    </section>
  )
}
