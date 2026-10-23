// The on-page mode: each problem the check found is highlighted where it sits in the posting, with a card
// beside it to accept or skip the fix. OnPage.tsx injects this file into the posting's frame with
// chrome.scripting, once per page, so it imports nothing and keeps itself on `window` (the extension's
// own world there, not the page's).
//
// Highlights use the CSS Custom Highlight API, so the editor's DOM isn't touched until a fix is accepted;
// a textarea gets a see-through copy of its text with the marks instead. The cards live in a closed
// shadow root on <html>. An accepted fix is written the way typing would be: select the text, then
// insert, so the editor's own model and its undo see the change.

export interface OverlayItem {
  id: string
  /** A fix to accept, or a problem to fix by hand. */
  kind: "fix" | "note"
  title: string
  why: string
  /** The problem text as the check quotes it; "" where a fix adds text. */
  target: string
  /** The checked text just before and after it: tells repeats apart, and says where an insert goes. */
  prefix: string
  suffix: string
  /** The new wording ("" removes the text); null until a pay range is picked from `options`. */
  fix?: string | null
  options?: string[]
  optional?: boolean
}

export interface OverlayShow {
  key: string
  items: OverlayItem[]
  /** The posting came from a field CheckON can write into; else the cards offer Copy fix. */
  editable: boolean
}

export type ItemState = "open" | "applied" | "skipped" | "copied" | "missing"

/** Sent to the side panel whenever something changes on the page. */
export interface OverlayStatus {
  type: "checkon-overlay"
  key: string
  visible: boolean
  editable: boolean
  states: Record<string, { state: ItemState; option?: number }>
}

export interface Overlay {
  show(data: OverlayShow): void
  acceptAll(): Promise<void>
  hide(): void
}

declare global {
  interface Window {
    __checkonOverlay?: Overlay
  }
}

const MARK = "data-checkon-target"

const folds = (chars: string, to: string) =>
  Object.fromEntries([...chars].map((ch) => [ch, to]))
// The folds the check applies to a posting (backend/app/compliance/normalise.py), so the page's text
// matches the text the check quotes.
const FOLD: Record<string, string> = {
  ...folds("\t              　", " "),
  ...folds("​‌‍⁠﻿­", ""),
  ...folds("‘’‚‛′", "'"),
  ...folds("“”„‟″", '"'),
  ...folds("‐‑‒–—―−", "-"),
  ...folds("  \u000b\u000c\u0085", "\n"),
  "…": "...",
}
// A list marker at the start of a line: the check keeps "• ", an editor's <li> has none.
const BULLET = /^(?:[-*•·▪◦‣○●■□➢➤✓✔]|\d{1,2}[.)]|[a-z][.)])\s+/
const BLOCKS = new Set(
  "ADDRESS ARTICLE ASIDE BLOCKQUOTE BR DD DIV DL DT FIELDSET FIGCAPTION FIGURE FOOTER FORM H1 H2 H3 H4 H5 H6 HEADER HR LI MAIN NAV OL P PRE SECTION TABLE TD TH TR UL".split(
    " ",
  ),
)
const SKIP = new Set(
  "SCRIPT STYLE TEMPLATE NOSCRIPT TEXTAREA SELECT IFRAME svg".split(" "),
)

/** Text as the check reads it (folded, one space for any run of white space, no list markers), with where
 * each character came from. */
class FlatText<P> {
  chars: string[] = []
  at: (P | null)[] = []
  /** The spaces that stand for a line or block break. */
  breaks = new Set<number>()
  private lineStart = true

  constructor(lineStart = true) {
    this.lineStart = lineStart
  }

  brk() {
    const last = this.chars.length - 1
    if (last >= 0) {
      if (this.chars[last] !== " ") {
        this.chars.push(" ")
        this.at.push(null)
      }
      this.breaks.add(this.chars.length - 1)
    }
    this.lineStart = true
  }

  /** `pre`: a newline is a line break (plain text), not a space (HTML). */
  add(data: string, point: (index: number) => P, pre: boolean) {
    for (let i = 0; i < data.length; i++) {
      const ch = data[i]
      const folded = ch === "\r" ? "\n" : (FOLD[ch] ?? ch)
      if (!folded) continue
      if (folded === "\n" && pre) {
        this.brk()
        continue
      }
      if (/^\s$/.test(folded)) {
        if (this.chars.length && this.chars[this.chars.length - 1] !== " ") {
          this.chars.push(" ")
          this.at.push(point(i))
        }
        continue
      }
      if (this.lineStart) {
        this.lineStart = false
        const marker = BULLET.exec(data.slice(i, i + 6))
        if (marker) {
          i += marker[0].length - 1
          continue
        }
      }
      for (const out of folded) {
        this.chars.push(out)
        this.at.push(point(i))
      }
    }
  }

  get text() {
    return this.chars.join("")
  }

  /** The first character from the page at or after `index`. */
  firstReal(index: number): number | null {
    for (let i = index; i < this.at.length; i++) if (this.at[i]) return i
    return null
  }

  /** The last character from the page at or before `index`. */
  lastReal(index: number): number | null {
    for (let i = index; i >= 0; i--) if (this.at[i]) return i
    return null
  }
}

type DomPoint = [Text, number]

function squash(text: string, lineStart = true): string {
  const flat = new FlatText<number>(lineStart)
  flat.add(text, (i) => i, true)
  return flat.text.trim()
}

function readDom(root: Node, skip: Node): FlatText<DomPoint> {
  const flat = new FlatText<DomPoint>()
  const walk = (node: Node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node as Text
      flat.add(text.data, (i) => [text, i], false)
      return
    }
    if (!(node instanceof Element) || node === skip || SKIP.has(node.tagName))
      return
    if (node !== root && !node.checkVisibility()) return
    const block = BLOCKS.has(node.tagName)
    if (block) flat.brk()
    for (const child of node.childNodes) walk(child)
    if (block) flat.brk()
  }
  walk(root)
  return flat
}

function readValue(value: string): FlatText<number> {
  const flat = new FlatText<number>()
  flat.add(value, (i) => i, true)
  return flat
}

function common(a: string, b: string, fromEnd: boolean): number {
  const max = Math.min(a.length, b.length)
  let n = 0
  while (
    n < max &&
    (fromEnd ? a[a.length - 1 - n] === b[b.length - 1 - n] : a[n] === b[n])
  )
    n++
  return n
}

/** Where `target` sits in `text`: the occurrence whose surroundings match best. An insert (no target)
 * goes just after the text before it, or just before the text after it. */
function place(
  text: string,
  target: string,
  prefix: string,
  suffix: string,
): [number, number] | null {
  const score = (start: number, end: number) =>
    common(
      text.slice(Math.max(0, start - prefix.length - 2), start).trimEnd(),
      prefix,
      true,
    ) +
    common(text.slice(end, end + suffix.length + 2).trimStart(), suffix, false)
  const best = (needle: string, span: (index: number) => [number, number]) => {
    let found: [number, number] | null = null
    let top = -1
    for (
      let i = text.indexOf(needle);
      i >= 0;
      i = text.indexOf(needle, i + 1)
    ) {
      const candidate = span(i)
      const value = score(...candidate)
      if (value > top) {
        top = value
        found = candidate
      }
    }
    return found
  }
  if (target) return best(target, (i) => [i, i + target.length])
  const lead = prefix.slice(-40).trimStart()
  if (lead) return best(lead, (i) => [i + lead.length, i + lead.length])
  const tail = suffix.slice(0, 40).trimEnd()
  if (tail) return best(tail, (i) => [i, i])
  return null
}

const tick = (ms = 30) => new Promise((resolve) => setTimeout(resolve, ms))
const exec = (command: string, value?: string) =>
  document.execCommand(command, false, value)

interface Entry {
  item: OverlayItem
  state: Exclude<ItemState, "missing">
  option?: number
  /** The wording written in, shown in green; gone again means the change was undone. */
  written?: string
  writtenAt?: number
  error?: string
  /** Where it sits now (from the last relocate): in the flat text, and on the page. */
  span?: [number, number]
  range?: Range
  offsets?: [number, number]
  done?: Range
  doneOffsets?: [number, number]
}

const STYLE = `
:host { all: initial; }
* { box-sizing: border-box; }
.layer { position: fixed; inset: 0; pointer-events: none; z-index: 2147483647;
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #1c1917; }
button { font: inherit; cursor: pointer; border-radius: 8px; border: 1px solid #d6d3d1; background: #fff;
  color: inherit; padding: 5px 11px; }
button:hover { background: #f5f5f4; }
button:disabled { opacity: .5; cursor: default; }
button:focus-visible { outline: 2px solid #0f766e; outline-offset: 1px; }
button.primary { background: #0f766e; border-color: #0f766e; color: #fff; }
button.primary:hover { background: #115e59; }
button.icon { border: 0; background: transparent; padding: 2px 7px; color: #57534e; }
.card, .bar { pointer-events: auto; background: #fff; border: 1px solid #e7e5e4;
  box-shadow: 0 12px 32px rgb(0 0 0 / .16), 0 2px 6px rgb(0 0 0 / .08); }
.card { position: fixed; width: 340px; max-width: calc(100vw - 16px); border-radius: 12px; padding: 12px 14px; }
.head { display: flex; align-items: center; gap: 8px; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: #eab308; flex: none; }
.title { font-weight: 600; flex: 1; }
.count { font-size: 12px; color: #78716c; }
.badge { font-size: 11px; border: 1px solid #d6d3d1; border-radius: 999px; padding: 0 7px; color: #57534e; }
.why { margin: 6px 0 0; font-size: 13px; color: #57534e; display: -webkit-box; -webkit-line-clamp: 3;
  -webkit-box-orient: vertical; overflow: hidden; }
.del, .ins { margin: 8px 0 0; padding: 6px 9px; border-radius: 7px; font-size: 13px; white-space: pre-line; }
.del { background: #fef2f2; color: #991b1b; text-decoration: line-through; text-decoration-color: #f87171; }
.ins { background: #ecfdf5; color: #065f46; }
.pick { margin: 8px 0 0; font-size: 13px; color: #57534e; }
.options { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.options button[aria-pressed="true"] { background: #0f766e; border-color: #0f766e; color: #fff; }
.error { margin: 8px 0 0; font-size: 13px; color: #b45309; }
.foot { display: flex; align-items: center; gap: 6px; margin-top: 10px; }
.foot .nav { margin-left: auto; display: flex; }
.bar { position: fixed; right: 16px; bottom: 16px; display: flex; align-items: center; gap: 8px;
  border-radius: 999px; padding: 6px 6px 6px 14px; max-width: calc(100vw - 32px); }
.brand { font-weight: 700; color: #0f766e; }
.summary { color: #57534e; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pin { position: fixed; width: 18px; height: 18px; margin: -9px 0 0 -2px; border-radius: 50%; border: 0;
  padding: 0; background: #eab308; color: #422006; font: 700 13px/18px system-ui, sans-serif; text-align: center;
  pointer-events: auto; box-shadow: 0 1px 3px rgb(0 0 0 / .3); }
.pin.active { background: #ca8a04; color: #fff; }
.mirror { position: fixed; overflow: hidden; pointer-events: none; }
.mirror > div { color: transparent; white-space: pre-wrap; overflow-wrap: break-word; margin: 0;
  border-style: solid; border-color: transparent; }
.mirror mark { color: transparent; background: rgb(250 204 21 / .45); border-radius: 2px; }
.mirror mark.active { background: rgb(250 204 21 / .9); }
.mirror mark.done { background: rgb(52 211 153 / .3); }
.mirror .spot { position: relative; display: inline-block; width: 0; height: 1em; vertical-align: text-bottom; }
.mirror .pin { position: absolute; left: 2px; top: 50%; margin: -9px 0 0; }
`

// The marks themselves: ::highlight() rules only work from the page's own style sheets.
const PAGE_STYLE = `
::highlight(checkon-open) { background-color: rgb(250 204 21 / 0.45); }
::highlight(checkon-active) { background-color: rgb(250 204 21 / 0.9); text-decoration: underline 2px rgb(161 98 7); }
::highlight(checkon-done) { background-color: rgb(52 211 153 / 0.3); }
`

const COPY_ONLY =
  "CheckON couldn't write into this editor. Copy the fix and paste it in instead."

function createOverlay(): Overlay {
  let data: OverlayShow | null = null
  let key = ""
  let entries: Entry[] = []
  let current: Entry | null = null
  let busy = false
  /** The field fixes are written into; null on a page CheckON only reads. */
  let field: HTMLElement | null = null
  let root: HTMLElement = document.body
  let flatDom: FlatText<DomPoint> | null = null
  let flatValue: FlatText<number> | null = null
  let host: HTMLElement | null = null
  let layer: HTMLDivElement
  let card: HTMLDivElement
  let bar: HTMLDivElement
  let pins: HTMLDivElement
  let mirror: HTMLDivElement
  let pageStyle: HTMLStyleElement | null = null
  let observer: MutationObserver | null = null
  let frame = 0

  const textarea = () => (field instanceof HTMLTextAreaElement ? field : null)

  const h = <K extends keyof HTMLElementTagNameMap>(
    tag: K,
    className = "",
    ...children: (Node | string | null | false | undefined)[]
  ) => {
    const node = document.createElement(tag)
    if (className) node.className = className
    for (const child of children) if (child) node.append(child)
    return node
  }
  const button = (
    label: string,
    onClick: () => void,
    className = "",
    title = "",
  ) => {
    const node = h("button", className, label)
    node.type = "button"
    if (title) node.setAttribute("aria-label", title)
    node.addEventListener("click", (event) => {
      event.stopPropagation()
      onClick()
    })
    return node
  }

  // Where each item sits

  function relocate() {
    const area = textarea()
    let text: string
    if (area) {
      flatValue = readValue(area.value)
      flatDom = null
      text = flatValue.text
    } else {
      flatDom = readDom(root, host ?? document.createElement("i"))
      flatValue = null
      text = flatDom.text
    }
    const squashed = (item: OverlayItem) => ({
      target: squash(item.target, !item.prefix || /\n$/.test(item.prefix)),
      prefix: squash(item.prefix, false),
      suffix: squash(item.suffix, /\n$/.test(item.target)),
    })
    let changed = false
    // Fixes already written first: an insert at the same place goes after them, in the check's order.
    const written: [number, number][] = []
    for (const entry of entries) {
      entry.done = undefined
      entry.doneOffsets = undefined
      if (entry.state !== "applied") continue
      const { target, prefix, suffix } = squashed(entry.item)
      entry.span = place(text, target, prefix, suffix) ?? undefined
      locate(entry, entry.span, "range", "offsets")
      const wording = squash(entry.written ?? "")
      const done = wording ? place(text, wording, prefix, suffix) : null
      locate(entry, done ?? undefined, "done", "doneOffsets")
      if (done) written.push(done)
      // Undone (Ctrl+Z): the new wording is gone, or the removed text is back where it was.
      const settled = Date.now() - (entry.writtenAt ?? 0) > 1000
      const undone = wording
        ? !done
        : entry.span &&
          common(text.slice(0, entry.span[0]).trimEnd(), prefix, true) >
            Math.min(prefix.length, 20)
      if (settled && undone) {
        entry.state = "open"
        entry.written = undefined
        changed = true
      }
    }
    for (const entry of entries) {
      if (entry.state === "applied") continue
      const { target, prefix, suffix } = squashed(entry.item)
      let span = place(text, target, prefix, suffix)
      for (let moved = !target; span && moved; ) {
        moved = false
        for (const done of written)
          if (done[0] >= span[0] && done[0] - span[0] <= 2) {
            span = [done[1], done[1]]
            moved = true
          }
      }
      // Already on the page (written before, or by hand): count it as fixed.
      const fix = fixFor(entry)
      const wording = entry.state === "open" && fix ? squash(fix) : ""
      const found =
        wording && (!span || !target)
          ? place(text, wording, prefix, suffix)
          : null
      if (
        found &&
        (target || (span && found[0] - span[0] >= 0 && found[0] - span[0] <= 2))
      ) {
        entry.state = "applied"
        entry.written = fix ?? ""
        entry.writtenAt = 0
        locate(entry, found, "done", "doneOffsets")
        written.push(found)
        changed = true
      }
      entry.span = span ?? undefined
      locate(entry, entry.span, "range", "offsets")
    }
    if (changed) emit()
  }

  /** Turn a span of the flat text into a DOM range or textarea offsets on the entry. */
  function locate(
    entry: Entry,
    span: [number, number] | undefined,
    rangeKey: "range" | "done",
    offsetsKey: "offsets" | "doneOffsets",
  ) {
    entry[rangeKey] = undefined
    entry[offsetsKey] = undefined
    if (!span) return
    const [start, end] = span
    if (flatValue) {
      const at = flatValue.at
      if (start === end) {
        const before = flatValue.lastReal(start - 1)
        const pos = before === null ? 0 : (at[before] as number) + 1
        entry[offsetsKey] = [pos, pos]
        return
      }
      const first = flatValue.firstReal(start)
      const last = flatValue.lastReal(end - 1)
      if (first === null || last === null) return
      entry[offsetsKey] = [at[first] as number, (at[last] as number) + 1]
      return
    }
    if (!flatDom) return
    const at = flatDom.at
    const range = document.createRange()
    if (start === end) {
      const before = flatDom.lastReal(start - 1)
      const after = flatDom.firstReal(start)
      if (before !== null) range.setStart(at[before]![0], at[before]![1] + 1)
      else if (after !== null) range.setStart(at[after]![0], at[after]![1])
      else return
      range.collapse(true)
    } else {
      const first = flatDom.firstReal(start)
      const last = flatDom.lastReal(end - 1)
      if (first === null || last === null) return
      range.setStart(at[first]![0], at[first]![1])
      range.setEnd(at[last]![0], at[last]![1] + 1)
    }
    entry[rangeKey] = range
  }

  const ordered = () =>
    entries
      .filter((entry) => entry.span)
      .sort((a, b) => a.span![0] - b.span![0])
  const isOpen = (entry: Entry) => entry.state === "open" && !!entry.span

  // Drawing

  function paint() {
    const area = textarea()
    if (area) {
      CSS.highlights.delete("checkon-open")
      CSS.highlights.delete("checkon-active")
      CSS.highlights.delete("checkon-done")
      drawMirror(area)
      return
    }
    const marks = new Highlight()
    const active = new Highlight()
    const done = new Highlight()
    active.priority = 2
    done.priority = 1
    for (const entry of entries) {
      if (entry.done) done.add(entry.done)
      if (!isOpen(entry) || !entry.range || entry.range.collapsed) continue
      ;(entry === current ? active : marks).add(entry.range)
    }
    CSS.highlights.set("checkon-open", marks)
    CSS.highlights.set("checkon-active", active)
    CSS.highlights.set("checkon-done", done)
    pins.replaceChildren(
      ...entries
        .filter((entry) => isOpen(entry) && entry.range?.collapsed)
        .map((entry) => {
          const pin = button("+", () => open(entry), "pin", entry.item.title)
          pin.dataset.id = entry.item.id
          if (entry === current) pin.classList.add("active")
          return pin
        }),
    )
  }

  const COPIED = [
    "fontFamily",
    "fontSize",
    "fontWeight",
    "fontStyle",
    "fontVariant",
    "fontStretch",
    "letterSpacing",
    "wordSpacing",
    "lineHeight",
    "textIndent",
    "textTransform",
    "textAlign",
    "tabSize",
    "wordBreak",
    "direction",
    "paddingTop",
    "paddingRight",
    "paddingBottom",
    "paddingLeft",
    "borderTopWidth",
    "borderRightWidth",
    "borderBottomWidth",
    "borderLeftWidth",
  ] as const

  /** A textarea's text can't be highlighted in place: draw a see-through copy with the marks over it. */
  function drawMirror(area: HTMLTextAreaElement) {
    const marks: { start: number; end: number; entry: Entry; kind: string }[] =
      []
    for (const entry of entries) {
      if (entry.doneOffsets)
        marks.push({
          start: entry.doneOffsets[0],
          end: entry.doneOffsets[1],
          entry,
          kind: "done",
        })
      if (isOpen(entry) && entry.offsets)
        marks.push({
          start: entry.offsets[0],
          end: entry.offsets[1],
          entry,
          kind: entry === current ? "active" : "",
        })
    }
    marks.sort((a, b) => a.start - b.start || a.end - b.end)
    const value = area.value
    const inner = h("div")
    let cursor = 0
    for (const mark of marks) {
      if (mark.start < cursor) continue
      inner.append(value.slice(cursor, mark.start))
      if (mark.start === mark.end) {
        // A zero-width spot, so the pin doesn't push the copied text out of line with the textarea's.
        const spot = h(
          "span",
          "spot",
          button(
            "+",
            () => open(mark.entry),
            `pin${mark.kind === "active" ? " active" : ""}`,
            mark.entry.item.title,
          ),
        )
        spot.dataset.id = mark.entry.item.id
        inner.append(spot)
      } else {
        const node = h("mark", mark.kind, value.slice(mark.start, mark.end))
        node.dataset.id = mark.entry.item.id
        inner.append(node)
      }
      cursor = mark.end
    }
    inner.append(`${value.slice(cursor)}​`)
    mirror.replaceChildren(inner)
    placeMirror(area)
  }

  function placeMirror(area: HTMLTextAreaElement) {
    const inner = mirror.firstElementChild as HTMLDivElement | null
    if (!inner) return
    const box = area.getBoundingClientRect()
    const style = getComputedStyle(area)
    Object.assign(mirror.style, {
      left: `${box.left}px`,
      top: `${box.top}px`,
      width: `${box.width}px`,
      height: `${box.height}px`,
    })
    for (const name of COPIED) inner.style[name] = style[name]
    const borders =
      Number.parseFloat(style.borderLeftWidth) +
      Number.parseFloat(style.borderRightWidth)
    inner.style.boxSizing = "border-box"
    inner.style.width = `${area.clientWidth + borders}px`
    inner.style.minHeight = `${box.height}px`
    inner.style.transform = `translate(${-area.scrollLeft}px, ${-area.scrollTop}px)`
  }

  function anchorRect(entry: Entry): DOMRect | null {
    if (textarea()) {
      const node = mirror.querySelector(
        `[data-id="${CSS.escape(entry.item.id)}"]`,
      )
      return node?.getBoundingClientRect() ?? null
    }
    const range = entry.range
    if (!range) return null
    if (!range.collapsed) return range.getBoundingClientRect()
    const rect = range.getClientRects()[0] ?? range.getBoundingClientRect()
    if (rect.width || rect.height || rect.top || rect.left) return rect
    const parent = range.startContainer.parentElement
    if (!parent) return null
    const box = parent.getBoundingClientRect()
    return new DOMRect(box.right, box.top, 0, Math.min(box.height, 20))
  }

  /** Move the card, pins and textarea copy to where their text is now. */
  function layout() {
    frame = 0
    const area = textarea()
    if (area) placeMirror(area)
    for (const pin of pins.querySelectorAll<HTMLElement>(".pin")) {
      const entry = entries.find((e) => e.item.id === pin.dataset.id)
      const rect = entry && anchorRect(entry)
      pin.hidden = !rect
      if (rect) {
        pin.style.left = `${rect.right}px`
        pin.style.top = `${rect.top + rect.height / 2}px`
      }
    }
    if (!current) return
    const rect = anchorRect(current)
    const gap = 8
    // Text scrolled out of the editor's own box is hidden too.
    const clip =
      field?.getBoundingClientRect() ??
      new DOMRect(0, 0, innerWidth, innerHeight)
    const visible =
      rect &&
      rect.bottom > Math.max(0, clip.top) &&
      rect.top < Math.min(innerHeight, clip.bottom) &&
      rect.right > 0
    card.style.visibility = visible ? "visible" : "hidden"
    if (!rect || !visible) return
    const { width, height } = card.getBoundingClientRect()
    let top = rect.bottom + gap
    if (top + height > innerHeight - gap && rect.top - gap - height > gap)
      top = rect.top - gap - height
    const left = Math.min(
      Math.max(gap, rect.left),
      Math.max(gap, innerWidth - width - gap),
    )
    card.style.top = `${Math.max(gap, top)}px`
    card.style.left = `${left}px`
  }
  const schedule = () => {
    if (!frame) frame = requestAnimationFrame(layout)
  }

  function renderCard() {
    card.replaceChildren()
    card.hidden = !current
    if (!current) return
    const entry = current
    const { item } = entry
    const list = ordered()
    const index = list.indexOf(entry)
    const note = item.kind === "note"
    const options = item.options ?? []
    const fix = fixFor(entry)

    card.append(
      h(
        "div",
        "head",
        h("span", "dot"),
        h("span", "title", item.title),
        note && h("span", "badge", "Fix this yourself"),
        item.optional && h("span", "badge", "Optional"),
        h("span", "count", `${index + 1} of ${list.length}`),
        button("×", close, "icon", "Close"),
      ),
    )
    if (item.why) card.append(h("p", "why", item.why))
    if (!note) {
      if (item.target) card.append(h("p", "del", item.target.trim()))
      if (options.length) {
        const picks = h("div", "options")
        options.forEach((option, i) => {
          const pick = button(option, () => {
            entry.option = i
            renderCard()
            schedule()
          })
          pick.setAttribute("aria-pressed", String(entry.option === i))
          picks.append(pick)
        })
        card.append(
          h("p", "pick", "Pick the range you genuinely expect to pay:"),
          picks,
        )
      } else if (fix) card.append(h("p", "ins", fix.trim()))
    }
    if (entry.error) card.append(h("p", "error", entry.error))

    const foot = h("div", "foot")
    if (note) foot.append(button("Got it", () => decide(entry, "skipped")))
    else {
      const copyOnly = !field || !!entry.error
      const main = copyOnly
        ? button("Copy fix", () => copyFix(entry), "primary")
        : button("Accept", () => accept(entry), "primary")
      main.disabled = busy || fix === null || (copyOnly && !fix)
      foot.append(
        main,
        button("Skip", () => decide(entry, "skipped")),
      )
    }
    foot.append(
      h(
        "span",
        "nav",
        button("‹", () => step(-1), "icon", "Previous"),
        button("›", () => step(1), "icon", "Next"),
      ),
    )
    card.append(foot)
  }

  function renderBar() {
    const waiting = entries.filter(isOpen)
    const fixes = waiting.filter(
      (entry) =>
        entry.item.kind === "fix" &&
        !entry.item.optional &&
        fixFor(entry) !== null,
    )
    const applied = entries.filter((entry) => entry.state === "applied").length
    const missing = entries.filter(
      (entry) => entry.state === "open" && !entry.span,
    ).length
    const parts = [
      waiting.length
        ? `${waiting.length} to review`
        : entries.length
          ? "All reviewed"
          : "Nothing to fix here",
      applied && `${applied} fixed`,
      missing && `${missing} not found on the page`,
    ].filter(Boolean)
    const children = [
      h("span", "brand", "CheckON"),
      h("span", "summary", parts.join(" · ")),
      waiting.length > 0 && !current && button("Review", openFirst),
      field &&
        fixes.length > 1 &&
        button(
          `Accept all (${fixes.length})`,
          () => overlay.acceptAll(),
          "primary",
        ),
      button("×", () => overlay.hide(), "icon", "Hide CheckON highlights"),
    ]
    bar.replaceChildren(
      ...children.filter((child): child is HTMLElement => !!child),
    )
  }

  function render() {
    paint()
    renderCard()
    renderBar()
    schedule()
  }

  // Acting on a card

  const fixFor = (entry: Entry): string | null => {
    const options = entry.item.options ?? []
    if (options.length)
      return entry.option === undefined ? null : (options[entry.option] ?? null)
    return entry.item.fix ?? null
  }

  function open(entry: Entry, scroll = false) {
    current = entry
    render()
    if (scroll) reveal(entry)
  }
  function openFirst() {
    const first = ordered().find(isOpen)
    if (first) open(first, true)
  }
  function close() {
    current = null
    render()
  }
  function step(direction: number) {
    const list = ordered()
    if (!list.length) return
    const index = current ? list.indexOf(current) : -1
    open(list[(index + direction + list.length) % list.length], true)
  }
  /** After a decision: the next open item, else close. */
  function advance(from: Entry) {
    const list = ordered()
    const index = list.indexOf(from)
    const next =
      list.slice(index + 1).find(isOpen) ?? list.slice(0, index).find(isOpen)
    current = next ?? null
    render()
    if (next) reveal(next)
  }

  function reveal(entry: Entry) {
    const area = textarea()
    if (area) {
      const node = mirror.querySelector<HTMLElement>(
        `[data-id="${CSS.escape(entry.item.id)}"]`,
      )
      if (node)
        area.scrollTop = Math.max(0, node.offsetTop - area.clientHeight / 3)
      area.scrollIntoView({ block: "nearest", behavior: "smooth" })
      return
    }
    const rect = anchorRect(entry)
    if (rect && rect.top > 60 && rect.bottom < innerHeight - 200) return
    const node = entry.range?.startContainer
    const element = node instanceof Element ? node : node?.parentElement
    element?.scrollIntoView({ block: "center", behavior: "smooth" })
  }

  function decide(entry: Entry, state: Entry["state"]) {
    entry.state = state
    entry.error = undefined
    emit()
    advance(entry)
  }

  /** Copy the fix: a copy command that carries the text (it works inside the click, on any page), else
   * the clipboard API. Only a copy that happened counts. */
  async function copyFix(entry: Entry) {
    const fix = fixFor(entry)
    if (!fix) return
    const text = fix.trim()
    let copied = false
    const onCopy = (event: ClipboardEvent) => {
      event.clipboardData?.setData("text/plain", text)
      event.preventDefault()
      copied = true
    }
    document.addEventListener("copy", onCopy, true)
    try {
      copied = exec("copy") && copied
    } finally {
      document.removeEventListener("copy", onCopy, true)
    }
    if (!copied)
      copied = await navigator.clipboard.writeText(text).then(
        () => true,
        () => false,
      )
    if (copied) decide(entry, "copied")
    else {
      entry.error =
        "CheckON couldn't copy here. Select the new wording above and copy it."
      renderCard()
      schedule()
    }
  }

  async function accept(entry: Entry, next = true): Promise<boolean> {
    const fix = fixFor(entry)
    if (fix === null || !field || busy) return false
    busy = true
    renderCard()
    let written = false
    try {
      relocate()
      if (entry.span)
        written = textarea()
          ? await writeValue(entry, fix)
          : await writeDom(entry, fix)
    } catch {
      written = false
    }
    busy = false
    if (written) {
      entry.state = "applied"
      entry.written = fix
      entry.writtenAt = Date.now()
      entry.error = undefined
    } else entry.error = COPY_ONLY
    relocate()
    emit()
    if (written && next) advance(entry)
    else render()
    return written
  }

  // Writing a fix into the page

  /** A textarea: select the text and insert, which keeps the browser's undo and tells frameworks. */
  async function writeValue(entry: Entry, fix: string): Promise<boolean> {
    const area = textarea()!
    if (!entry.offsets) return false
    const value = area.value
    let [start, end] = entry.offsets
    if (!fix && start < end) {
      const lineStart = value.lastIndexOf("\n", start - 1) + 1
      const found = value.indexOf("\n", end)
      const lineEnd = found < 0 ? value.length : found
      const alone =
        !squash(value.slice(lineStart, start)) &&
        !value.slice(end, lineEnd).trim()
      if (alone) {
        start = lineStart
        end = lineEnd < value.length ? lineEnd + 1 : lineEnd
        if (lineEnd >= value.length) start = Math.max(0, lineStart - 1)
        // Don't leave two blank lines where one was.
        if (value.slice(start - 2, start) === "\n\n" && value[end] === "\n")
          end++
      } else if (value[end] === " ") end++
    }
    area.focus({ preventScroll: true })
    area.setSelectionRange(start, end)
    const inserted = fix ? exec("insertText", fix) : exec("delete")
    if (!inserted || area.value === value) {
      area.setRangeText(fix, start, end, "end")
      area.dispatchEvent(new Event("input", { bubbles: true }))
    }
    await tick()
    return area.value !== value
  }

  /** The range that removes a whole line or block (else the text and the space after it). */
  function deletion(entry: Entry): Range {
    const flat = flatDom!
    const [start, end] = entry.span!
    const range = entry.range!.cloneRange()
    const at = flat.at
    const whole =
      (start === 0 || flat.breaks.has(start - 1)) &&
      (end >= flat.chars.length || flat.breaks.has(end))
    if (whole) {
      // From the end of the block before to the end of this one, so the block itself goes.
      const before = flat.lastReal(start - 2)
      const after = flat.firstReal(end + 1)
      if (before !== null) range.setStart(at[before]![0], at[before]![1] + 1)
      else if (after !== null) range.setEnd(at[after]![0], at[after]![1])
      return range
    }
    if (flat.chars[end] === " " && at[end])
      range.setEnd(at[end]![0], at[end]![1] + 1)
    return range
  }

  const blockOf = (node: Node | null | undefined) => {
    let element = node instanceof Element ? node : (node?.parentElement ?? null)
    while (element && element !== field && !BLOCKS.has(element.tagName))
      element = element.parentElement
    return element
  }

  /** A rich editor: select the text, then type the fix in (Enter for each new line), so the editor's own
   * model and undo see it. A paste is the fallback for editors that ignore typed commands. */
  async function writeDom(entry: Entry, fix: string): Promise<boolean> {
    const editor = field!
    if (!entry.range) return false
    const before = readDom(editor, host!).text
    const range = fix ? entry.range.cloneRange() : deletion(entry)
    editor.focus({ preventScroll: true })
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
    await tick()

    const newLine = /^[ \t]*\n/.test(fix)
    const lines = fix.split("\n").filter((line) => line.trim())
    if (!range.collapsed && (newLine || !lines.length)) {
      exec("delete")
      await tick()
    }
    for (const [i, line] of lines.entries()) {
      if (i > 0 || newLine) {
        exec("insertParagraph")
        await tick()
        // A sentence after a list starts below it, like pressing Enter twice.
        const item = blockOf(window.getSelection()?.anchorNode)?.closest("li")
        if (item && !BULLET.test(line)) {
          exec("insertParagraph")
          await tick()
        }
      }
      const inList = !!blockOf(window.getSelection()?.anchorNode)?.closest("li")
      exec("insertText", inList ? line.replace(BULLET, "") : line)
      await tick()
    }
    if (readDom(editor, host!).text !== before) return true

    selection?.removeAllRanges()
    selection?.addRange(range)
    const clipboard = new DataTransfer()
    clipboard.setData("text/plain", fix.trim())
    editor.dispatchEvent(
      new ClipboardEvent("paste", {
        clipboardData: clipboard,
        bubbles: true,
        cancelable: true,
      }),
    )
    await tick(60)
    return readDom(editor, host!).text !== before
  }

  // Status for the side panel

  function emit() {
    const states: OverlayStatus["states"] = {}
    for (const entry of entries)
      states[entry.item.id] = {
        state: entry.state === "open" && !entry.span ? "missing" : entry.state,
        option: entry.option,
      }
    const status: OverlayStatus = {
      type: "checkon-overlay",
      key,
      visible: !!data,
      editable: !!field,
      states,
    }
    try {
      chrome.runtime.sendMessage(status).catch(() => {})
    } catch {
      // The extension was reloaded: this copy can't reach it any more.
    }
  }

  // Page events

  function onClick(event: MouseEvent) {
    if (host && event.composedPath().includes(host)) return
    const area = textarea()
    let hit: Entry | undefined
    if (area && event.target === area) {
      const at = area.selectionStart
      hit = entries.find(
        (entry) =>
          isOpen(entry) &&
          entry.offsets &&
          entry.offsets[0] <= at &&
          at <= entry.offsets[1] &&
          entry.offsets[0] < entry.offsets[1],
      )
    } else if (!area) {
      hit = entries.find(
        (entry) =>
          isOpen(entry) &&
          entry.range &&
          !entry.range.collapsed &&
          [...entry.range.getClientRects()].some(
            (rect) =>
              event.clientX >= rect.left &&
              event.clientX <= rect.right &&
              event.clientY >= rect.top &&
              event.clientY <= rect.bottom,
          ),
      )
    }
    if (hit) open(hit)
    else if (current) close()
  }
  function onKey(event: KeyboardEvent) {
    if (event.key === "Escape" && current) close()
  }
  let pending = 0
  /** The page changed (typing, an accepted fix, the editor redrawing): find everything again. */
  function onChange() {
    clearTimeout(pending)
    pending = window.setTimeout(() => {
      if (!data || busy) return
      relocate()
      render()
    }, 150)
  }

  function mount() {
    if (host) return
    host = document.createElement("checkon-overlay")
    host.style.cssText =
      "all: initial; position: fixed; top: 0; left: 0; width: 0; height: 0; z-index: 2147483647;"
    const shadow = host.attachShadow({ mode: "closed" })
    const style = document.createElement("style")
    style.textContent = STYLE
    layer = h("div", "layer")
    mirror = h("div", "mirror")
    pins = h("div")
    card = h("div", "card")
    card.setAttribute("role", "dialog")
    card.setAttribute("aria-label", "CheckON fix")
    bar = h("div", "bar")
    bar.setAttribute("role", "status")
    layer.append(mirror, pins, card, bar)
    shadow.append(style, layer)
    document.documentElement.append(host)
    pageStyle = document.createElement("style")
    pageStyle.textContent = PAGE_STYLE
    ;(document.head ?? document.documentElement).append(pageStyle)
    document.addEventListener("click", onClick, true)
    document.addEventListener("keydown", onKey, true)
    window.addEventListener("scroll", schedule, {
      capture: true,
      passive: true,
    })
    window.addEventListener("resize", schedule)
  }

  function watch() {
    observer?.disconnect()
    observer = null
    const area = textarea()
    if (area) {
      area.removeEventListener("input", onChange)
      area.addEventListener("input", onChange)
      return
    }
    observer = new MutationObserver(onChange)
    observer.observe(root, {
      subtree: true,
      childList: true,
      characterData: true,
    })
  }

  const overlay: Overlay = {
    show(next) {
      // Decisions carry over to a new version of the same check (answers, a confirmed pay range, shown
      // again after Hide) by what the fix says, since its id can change.
      const keyOf = (item: OverlayItem) =>
        [item.kind, item.target, item.fix ?? "", ...(item.options ?? [])].join(
          "\u0000",
        )
      const checkOf = (value: string) => value.split(":")[0]
      const before = new Map(
        checkOf(key) === checkOf(next.key)
          ? entries.map((entry) => [keyOf(entry.item), entry])
          : [],
      )
      data = next
      key = next.key
      const marked = document.querySelector<HTMLElement>(`[${MARK}]`)
      field = next.editable && marked ? marked : null
      root = field ?? document.body
      const currentId = current?.item.id
      entries = next.items.map((item) => {
        const old = before.get(keyOf(item))
        return old ? { ...old, item } : { item, state: "open" }
      })
      current = entries.find((entry) => entry.item.id === currentId) ?? null
      mount()
      watch()
      relocate()
      render()
      emit()
    },

    async acceptAll() {
      if (!field) return
      relocate()
      const ready = ordered()
        .filter(
          (entry) =>
            isOpen(entry) &&
            entry.item.kind === "fix" &&
            !entry.item.optional &&
            fixFor(entry) !== null,
        )
        // From the bottom up, so the page above stays put; fixes at one place keep the check's order.
        .sort(
          (a, b) =>
            b.span![0] - a.span![0] || entries.indexOf(a) - entries.indexOf(b),
        )
      for (const entry of ready) await accept(entry, false)
      current = null
      render()
    },

    hide() {
      data = null
      emit()
      observer?.disconnect()
      textarea()?.removeEventListener("input", onChange)
      document.removeEventListener("click", onClick, true)
      document.removeEventListener("keydown", onKey, true)
      window.removeEventListener("scroll", schedule, { capture: true })
      window.removeEventListener("resize", schedule)
      for (const name of ["checkon-open", "checkon-active", "checkon-done"])
        CSS.highlights.delete(name)
      host?.remove()
      pageStyle?.remove()
      host = null
      pageStyle = null
      current = null // entries stay, for Show again
    },
  }
  return overlay
}

if (!window.__checkonOverlay) window.__checkonOverlay = createOverlay()
