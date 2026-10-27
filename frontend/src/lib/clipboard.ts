/** Copy text, with HTML beside it when given, and say whether it worked. Uses the clipboard API; where that is
 * refused (an embedded browser such as the Claude app's pane, or an older one), copies through a hidden selection
 * instead, then gives the focus back to `focus` (the button that was clicked). */
export async function copyToClipboard(
  text: string,
  { html, focus }: { html?: string; focus?: HTMLElement } = {},
): Promise<boolean> {
  try {
    if (html !== undefined && "ClipboardItem" in window) {
      await navigator.clipboard.write([
        new ClipboardItem({
          "text/html": new Blob([html], { type: "text/html" }),
          "text/plain": new Blob([text], { type: "text/plain" }),
        }),
      ])
    } else {
      await navigator.clipboard.writeText(text)
    }
    return true
  } catch {
    return copyBySelection(text, html, focus)
  }
}

function copyBySelection(text: string, html?: string, focus?: HTMLElement) {
  const area = Object.assign(document.createElement("textarea"), {
    value: text,
    readOnly: true,
  })
  Object.assign(area.style, { position: "fixed", top: "0", opacity: "0" })
  // The copy command takes the selected text; the HTML goes in through the copy event
  const withHtml = (event: ClipboardEvent) => {
    if (html === undefined || !event.clipboardData) return
    event.clipboardData.setData("text/plain", text)
    event.clipboardData.setData("text/html", html)
    event.preventDefault()
  }
  document.body.append(area)
  document.addEventListener("copy", withHtml)
  area.focus({ preventScroll: true })
  area.select()
  try {
    return document.execCommand("copy")
  } catch {
    return false
  } finally {
    document.removeEventListener("copy", withHtml)
    area.remove()
    focus?.focus({ preventScroll: true })
  }
}
