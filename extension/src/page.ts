// Reading the posting from the page and writing the approved version back. The two `…InPage`
// functions run inside the page (chrome.scripting serialises them), so they must not use anything
// from this module's scope.

export type Source = "selection" | "field" | "page"

export interface PagePosting {
  text: string
  source: Source
  editable: boolean // the text came from a field we can write back into
  tabId: number
  frameId: number
}

/** In the page: the selected text, else the job-description field, else the page's main text. */
function readPostingInPage(): {
  text: string
  source: "selection" | "field" | "page"
  editable: boolean
} | null {
  const MARK = "data-checkon-target"
  const clean = (value: string) => value.replace(/ /g, " ").trim()
  const isField = (el: Element | null): el is HTMLElement =>
    !!el &&
    (el instanceof HTMLTextAreaElement ||
      (el instanceof HTMLElement && el.isContentEditable))
  const fieldText = (el: HTMLElement) =>
    clean(el instanceof HTMLTextAreaElement ? el.value : el.innerText)
  const outermostEditable = (el: HTMLElement) => {
    let node = el
    while (node.parentElement?.isContentEditable) node = node.parentElement
    return node
  }

  for (const marked of document.querySelectorAll(`[${MARK}]`)) {
    marked.removeAttribute(MARK)
  }
  const mark = (el: HTMLElement) => el.setAttribute(MARK, "1")

  // 1. Selected text, remembering the field it sits in so fixes can go back there.
  const selection = window.getSelection()
  const selected = clean(selection?.toString() ?? "")
  if (selected.length >= 40) {
    const anchor = selection?.anchorNode
    const host =
      anchor instanceof HTMLElement ? anchor : (anchor?.parentElement ?? null)
    const field =
      document.activeElement instanceof HTMLTextAreaElement
        ? document.activeElement
        : host?.isContentEditable
          ? outermostEditable(host)
          : null
    if (field) mark(field)
    return { text: selected, source: "selection", editable: !!field }
  }

  // 2. The focused field, else the longest visible one (job editors are the big box on the page).
  const visible = (el: HTMLElement) => {
    const box = el.getBoundingClientRect()
    return box.width > 60 && box.height > 24
  }
  let best: HTMLElement | null = null
  const active = document.activeElement
  if (isField(active) && fieldText(active).length >= 40) {
    best =
      active instanceof HTMLTextAreaElement ? active : outermostEditable(active)
  } else {
    let bestLength = 0
    for (const el of document.querySelectorAll<HTMLElement>(
      "textarea, [contenteditable]",
    )) {
      if (!isField(el) || !visible(el)) continue
      const field =
        el instanceof HTMLTextAreaElement ? el : outermostEditable(el)
      const length = fieldText(field).length
      if (length > bestLength) {
        best = field
        bestLength = length
      }
    }
  }
  if (best && fieldText(best).length >= 40) {
    mark(best)
    return { text: fieldText(best), source: "field", editable: true }
  }

  // 3. A published posting: the page's main content, read only.
  const main =
    document.querySelector<HTMLElement>("main, article, [role=main]") ??
    document.body
  const text = clean(main?.innerText ?? "")
  return text.length >= 40 ? { text, source: "page", editable: false } : null
}

/** In the page: replace the marked field's content, the way the editor expects to be edited. */
function writePostingInPage(html: string, text: string): boolean {
  const el = document.querySelector<HTMLElement>("[data-checkon-target]")
  if (!el) return false
  el.focus()
  if (el instanceof HTMLTextAreaElement) {
    // Use the native setter so frameworks that wrap the field see the change.
    const setValue = Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype,
      "value",
    )?.set
    setValue?.call(el, text)
    el.dispatchEvent(new Event("input", { bubbles: true }))
    el.dispatchEvent(new Event("change", { bubbles: true }))
    return true
  }
  const range = document.createRange()
  range.selectNodeContents(el)
  const selection = window.getSelection()
  selection?.removeAllRanges()
  selection?.addRange(range)
  // Rich-text editors handle insertHTML like a paste, keeping their own state in step.
  if (document.execCommand("insertHTML", false, html)) return true
  el.innerHTML = html
  el.dispatchEvent(new Event("input", { bubbles: true }))
  return true
}

async function activeTabId(): Promise<number | undefined> {
  const [tab] = await chrome.tabs.query({
    active: true,
    lastFocusedWindow: true,
  })
  return tab?.id
}

const RANK: Record<Source, number> = { selection: 0, field: 1, page: 2 }

/** Read the posting from the current tab. Throws when Chrome won't let us read the page. */
export async function readFromPage(): Promise<PagePosting | null> {
  const tabId = await activeTabId()
  if (tabId === undefined) return null
  const results = await chrome.scripting.executeScript({
    target: { tabId, allFrames: true },
    func: readPostingInPage,
  })
  const found = results
    .flatMap(({ result, frameId }) =>
      result ? [{ ...result, tabId, frameId }] : [],
    )
    .filter((item) => item.source !== "page" || item.frameId === 0)
    .sort(
      (a, b) =>
        RANK[a.source] - RANK[b.source] || b.text.length - a.text.length,
    )
  return found[0] ?? null
}

/** Write the approved posting into the field it was read from. */
export async function writeToPage(
  posting: PagePosting,
  html: string,
  text: string,
): Promise<boolean> {
  const results = await chrome.scripting.executeScript({
    target: { tabId: posting.tabId, frameIds: [posting.frameId] },
    func: writePostingInPage,
    args: [html, text],
  })
  return results.some(({ result }) => result === true)
}
