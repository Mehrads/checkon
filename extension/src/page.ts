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
  const clean = (value: string) => value.replace(/\u00a0/g, " ").trim()
  const isField = (el: Element | null): el is HTMLElement =>
    !!el &&
    (el instanceof HTMLTextAreaElement ||
      (el instanceof HTMLElement && el.isContentEditable))

  // Rich editors hold lists as <ul><li>, and innerText drops the bullets. Walk the DOM instead:
  // one line per list item with "• ", a blank line between other blocks, like a pasted posting.
  const BLOCKS = new Set([
    "P",
    "DIV",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    "UL",
    "OL",
    "LI",
    "SECTION",
    "ARTICLE",
    "HEADER",
    "FOOTER",
    "BLOCKQUOTE",
    "TABLE",
    "TR",
    "PRE",
  ])
  // A heading, or a short line that is all bold (how many editors mark section titles), is followed
  // by its body on the next line, which is how the check's editor recognises a heading again.
  type Line = { text: string; item: boolean; heading: boolean; bold: boolean }
  const asText = (root: Node) => {
    const lines: Line[] = []
    let line: Line | null = null
    let bullet = false
    const end = () => {
      const text = line?.text.replace(/\s+/g, " ").trim()
      if (line && text)
        lines.push({
          ...line,
          text,
          heading:
            line.heading || (line.bold && !line.item && text.length <= 80),
        })
      line = null
    }
    const walk = (
      node: Node,
      inItem: boolean,
      inHeading: boolean,
      inBold: boolean,
    ) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const value = node.textContent ?? ""
        if (!line) {
          if (!value.trim()) return
          line = {
            text: bullet ? "• " : "",
            item: inItem,
            heading: inHeading,
            bold: inBold,
          }
          bullet = false
        }
        if (value.trim() && !inBold) line.bold = false
        line.text += value
        return
      }
      if (
        !(node instanceof Element) &&
        node.nodeType !== Node.DOCUMENT_FRAGMENT_NODE
      )
        return
      const tag = node instanceof Element ? node.tagName : ""
      if (tag === "SCRIPT" || tag === "STYLE" || tag === "TEMPLATE") return
      if (tag === "BR") return end()
      const block = BLOCKS.has(tag)
      if (block) end()
      if (tag === "LI") bullet = true
      for (const child of node.childNodes)
        walk(
          child,
          inItem || tag === "LI",
          inHeading || /^H[1-6]$/.test(tag),
          inBold || tag === "STRONG" || tag === "B",
        )
      if (block) end()
    }
    walk(root, false, false, false)
    const gap = (previous: Line, current: Line) =>
      previous.heading || (previous.item && current.item) ? "\n" : "\n\n"
    return clean(
      lines
        .map((l, i) => (i === 0 ? "" : gap(lines[i - 1], l)) + l.text)
        .join(""),
    )
  }
  const fieldText = (el: HTMLElement) =>
    el instanceof HTMLTextAreaElement ? clean(el.value) : asText(el)
  const outermostEditable = (el: HTMLElement) => {
    let node = el
    while (node.parentElement?.isContentEditable) node = node.parentElement
    return node
  }

  for (const marked of document.querySelectorAll(`[${MARK}]`)) {
    marked.removeAttribute(MARK)
  }
  const mark = (el: HTMLElement) => el.setAttribute(MARK, "1")

  // 1. Selected text. Fixes can be written back only when the selection is the whole field:
  //    writing a checked part over the whole description would lose the rest of it.
  const selection = window.getSelection()
  const focused = document.activeElement
  let selected = ""
  if (focused instanceof HTMLTextAreaElement) {
    selected = clean(
      focused.value.slice(focused.selectionStart, focused.selectionEnd),
    )
  } else {
    const fragment = document.createDocumentFragment()
    for (let i = 0; i < (selection?.rangeCount ?? 0); i++) {
      fragment.append(selection!.getRangeAt(i).cloneContents())
    }
    selected = asText(fragment)
  }
  if (selected.length >= 40) {
    const anchor = selection?.anchorNode
    const host =
      anchor instanceof HTMLElement ? anchor : (anchor?.parentElement ?? null)
    const field =
      focused instanceof HTMLTextAreaElement
        ? focused
        : host?.isContentEditable
          ? outermostEditable(host)
          : null
    const whole = !!field && fieldText(field) === selected
    if (whole) mark(field)
    return { text: selected, source: "selection", editable: whole }
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
  // 1. Editors (ProseMirror, TinyMCE, CKEditor, Quill…) handle a paste themselves, so their own
  //    document stays in step with what they show. A handled paste is cancelled by the editor.
  const data = new DataTransfer()
  data.setData("text/html", html)
  data.setData("text/plain", text)
  const paste = new ClipboardEvent("paste", {
    clipboardData: data,
    bubbles: true,
    cancelable: true,
  })
  if (!el.dispatchEvent(paste)) return true
  // 2. A bare editable area: replace its content. (execCommand("insertHTML") would copy the
  //    first block's style, a heading, onto everything inserted.)
  el.innerHTML = html
  el.dispatchEvent(
    new InputEvent("input", {
      bubbles: true,
      inputType: "insertReplacementText",
    }),
  )
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
