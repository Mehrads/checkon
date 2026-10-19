import type { JSONContent } from "@tiptap/react"

// Plain text to the editor's document and back. Pasted postings carry their structure only in
// line breaks, bullets and short heading lines, so that is what is read here.

const BULLET = /^\s*(?:[-*•·▪◦‣○●■□➢➤✓✔]|(\d{1,2})[.)])\s+/

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
}

function isHeading(line: string, previous?: string, next?: string): boolean {
  const text = line.trim()
  if (!text || text.length > 80 || BULLET.test(line)) return false
  if (text.endsWith(":")) return true
  const words = text.split(/\s+/).length
  const letters = text.replace(/[^A-Za-z]/g, "")
  if (letters.length > 2 && text === text.toUpperCase() && words <= 8) {
    return true
  }
  const startsBlock = previous === undefined || previous.trim() === ""
  const hasBody = next !== undefined && next.trim() !== ""
  return words <= 6 && !/[.!?,;]$/.test(text) && startsBlock && hasBody
}

/** The posting as HTML: the first heading line is the title (h2), later ones are section heads (h3). */
export function textToHtml(text: string): string {
  const lines = text.replace(/\r\n?/g, "\n").split("\n")
  const out: string[] = []
  let list: { ordered: boolean; items: string[] } | null = null
  let seenHeading = false

  const closeList = () => {
    if (!list) return
    const tag = list.ordered ? "ol" : "ul"
    out.push(
      `<${tag}>${list.items.map((item) => `<li><p>${item}</p></li>`).join("")}</${tag}>`,
    )
    list = null
  }

  lines.forEach((line, index) => {
    const bullet = BULLET.exec(line)
    if (bullet) {
      const ordered = Boolean(bullet[1])
      if (list && list.ordered !== ordered) closeList()
      list ??= { ordered, items: [] }
      list.items.push(escapeHtml(line.slice(bullet[0].length).trim()))
      return
    }
    closeList()
    if (!line.trim()) return
    if (isHeading(line, lines[index - 1], lines[index + 1])) {
      const tag = seenHeading || index > 0 ? "h3" : "h2"
      seenHeading = true
      out.push(`<${tag}>${escapeHtml(line.trim())}</${tag}>`)
      return
    }
    out.push(`<p>${escapeHtml(line.trim())}</p>`)
  })
  closeList()
  return out.join("")
}

function inline(node: JSONContent): string {
  if (node.type === "text") return node.text ?? ""
  if (node.type === "hardBreak") return "\n"
  return (node.content ?? []).map(inline).join("")
}

/** Plain text for job boards that strip formatting: bullets as "•", a blank line before each heading. */
export function docToPlainText(doc: JSONContent): string {
  const blocks: string[] = []
  for (const node of doc.content ?? []) {
    switch (node.type) {
      case "heading":
        if (blocks.length) blocks.push("")
        blocks.push(inline(node))
        break
      case "bulletList":
      case "orderedList": {
        const start = Number(node.attrs?.start ?? 1)
        ;(node.content ?? []).forEach((item, index) => {
          const marker = node.type === "bulletList" ? "•" : `${start + index}.`
          blocks.push(`${marker} ${(item.content ?? []).map(inline).join(" ")}`)
        })
        break
      }
      case "blockquote":
        for (const child of node.content ?? []) blocks.push(inline(child))
        break
      default:
        blocks.push(inline(node))
    }
  }
  return blocks.join("\n").trim()
}

export function countWords(text: string): number {
  const trimmed = text.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
}
