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

  // 3. A published posting: the page's main content, read only. An application form under the posting
  //    (Greenhouse, Lever) isn't part of it, unless the form is all there is (a page wrapped in one form).
  const main =
    document.querySelector<HTMLElement>("main, article, [role=main]") ??
    document.body
  let text = main?.innerText ?? ""
  let withoutForms = text
  for (const form of main?.querySelectorAll<HTMLElement>("form") ?? []) {
    const part = form.innerText.trim()
    if (part) withoutForms = withoutForms.replace(part, "")
  }
  withoutForms = withoutForms.replace(/\n{3,}/g, "\n\n")
  if (clean(withoutForms).length >= 200) text = withoutForms
  text = clean(text)
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

/** In the page: the application form's questions as text, one per line with " *" when required and its
 * choices on "- " lines after it (the format the check reads). The selected text wins, for a form builder
 * that shows its questions as text; else the form with the most visible fields. */
function readFormInPage(): {
  text: string
  questions: number
  source: "selection" | "form"
} | null {
  const clean = (value: string) => value.replace(/\s+/g, " ").trim()
  const selected = window.getSelection()?.toString().trim() ?? ""
  if (selected.length >= 10) {
    const lines = selected.split(/\n+/).filter((line) => line.trim())
    return { text: selected, questions: lines.length, source: "selection" }
  }

  const SKIP = new Set([
    "hidden",
    "submit",
    "button",
    "reset",
    "image",
    "search",
  ])
  const visible = (el: Element) => {
    const box = el.getBoundingClientRect()
    const style = getComputedStyle(el)
    return (
      (box.width > 0 || box.height > 0) &&
      style.visibility !== "hidden" &&
      style.display !== "none"
    )
  }
  const textOf = (ids: string | null) =>
    clean(
      (ids ?? "")
        .split(/\s+/)
        .map((id) => document.getElementById(id)?.textContent ?? "")
        .join(" "),
    )
  const labelOf = (el: HTMLElement): string => {
    const labelled = textOf(el.getAttribute("aria-labelledby"))
    if (labelled) return labelled
    const labels = (el as HTMLInputElement).labels
    if (labels?.length) return clean(labels[0].innerText)
    const aria = clean(el.getAttribute("aria-label") ?? "")
    if (aria) return aria
    // A field without a label: the text of the nearest block above it that has some.
    let node: HTMLElement | null = el
    for (let depth = 0; node && depth < 4; depth++) {
      let sibling = node.previousElementSibling
      while (sibling) {
        const text = clean((sibling as HTMLElement).innerText ?? "")
        if (text && text.length <= 300) return text
        sibling = sibling.previousElementSibling
      }
      node = node.parentElement
    }
    return clean(el.getAttribute("placeholder") ?? "")
  }
  /** The question for a group of radios or checkboxes: its fieldset legend or labelled group. */
  const groupLabelOf = (el: HTMLElement): string => {
    const group = el.closest<HTMLElement>(
      "fieldset, [role=radiogroup], [role=group]",
    )
    if (group) {
      const legend = group.querySelector("legend")
      if (legend) return clean(legend.innerText)
      const named =
        textOf(group.getAttribute("aria-labelledby")) ||
        clean(group.getAttribute("aria-label") ?? "")
      if (named) return named
    }
    const container = el.closest("label")?.parentElement ?? el.parentElement
    return container ? labelOf(container) : ""
  }

  type Question = { text: string; required: boolean; options: string[] }
  const read = (root: ParentNode): Question[] => {
    const questions: Question[] = []
    const groups = new Map<string, Question>()
    const fields = root.querySelectorAll<HTMLElement>(
      "input, select, textarea, [role=radiogroup], [role=combobox]",
    )
    for (const el of fields) {
      if (
        !visible(el) &&
        !(el instanceof HTMLInputElement && el.type === "radio")
      )
        continue
      if (el instanceof HTMLInputElement && SKIP.has(el.type)) continue
      // Custom dropdowns keep a hidden copy of the field for the browser's own required check.
      if (el.closest("[aria-hidden=true]")) continue
      const required =
        (el as HTMLInputElement).required ||
        el.getAttribute("aria-required") === "true"
      if (
        el instanceof HTMLInputElement &&
        (el.type === "radio" || el.type === "checkbox")
      ) {
        const option = labelOf(el)
        const name = el.name || option
        const peers = el.name
          ? root.querySelectorAll(`input[name="${CSS.escape(el.name)}"]`).length
          : 1
        if (peers <= 1 && el.type === "checkbox") {
          if (option) questions.push({ text: option, required, options: [] })
          continue
        }
        let group = groups.get(name)
        if (!group) {
          group = { text: groupLabelOf(el), required, options: [] }
          groups.set(name, group)
          questions.push(group)
        }
        group.required ||= required
        if (option && option !== group.text) group.options.push(option)
        continue
      }
      if (el.getAttribute("role") === "radiogroup") {
        const options = [...el.querySelectorAll<HTMLElement>("[role=radio]")]
          .map((radio) =>
            clean(radio.innerText || radio.getAttribute("aria-label") || ""),
          )
          .filter(Boolean)
        if (options.length)
          questions.push({ text: labelOf(el), required, options })
        continue
      }
      const options =
        el instanceof HTMLSelectElement
          ? [...el.options]
              .filter((option) => option.value !== "" && clean(option.text))
              .map((option) => clean(option.text))
          : []
      questions.push({ text: labelOf(el), required, options })
    }
    // A labelled wrapper and its field (a combobox around an input) read as one question, and a dropdown's
    // placeholder ("Select...") isn't one.
    const PLACEHOLDER =
      /^[-–\s]*(please\s+)?(select|choose|pick)(\s+(one|an option))?[\s.…-]*$/i
    return questions.filter(
      (question, i) =>
        question.text &&
        !PLACEHOLDER.test(question.text) &&
        !(
          i > 0 &&
          question.text === questions[i - 1].text &&
          !question.options.length
        ),
    )
  }

  const forms = [...document.querySelectorAll("form")]
    .map((form) => read(form))
    .sort((a, b) => b.length - a.length)
  const questions = forms[0]?.length ? forms[0] : read(document)
  if (!questions.length) return null
  const text = questions
    .map(({ text, required, options }) => {
      const star = /\*\s*$/.test(text)
      const line = `${text.replace(/\s*\*\s*$/, "")}${required || star ? " *" : ""}`
      return [line, ...options.map((option) => `- ${option}`)].join("\n")
    })
    .join("\n")
  return { text, questions: questions.length, source: "form" }
}

export interface PageForm {
  text: string
  questions: number
  source: "selection" | "form"
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

/** Read the application form from the current tab: the frame with the most questions. Throws when Chrome won't
 * let us read the page. */
export async function readFormFromPage(): Promise<PageForm | null> {
  const tabId = await activeTabId()
  if (tabId === undefined) return null
  const results = await chrome.scripting.executeScript({
    target: { tabId, allFrames: true },
    func: readFormInPage,
  })
  const found = results
    .flatMap(({ result }) => (result ? [result] : []))
    .sort(
      (a, b) =>
        Number(b.source === "selection") - Number(a.source === "selection") ||
        b.questions - a.questions,
    )
  return found[0] ?? null
}
