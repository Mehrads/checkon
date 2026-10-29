import { Check, Copy } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { copyToClipboard } from "@/lib/clipboard"

/** Copies `text`, says "Copied" for two seconds, then runs `onCopied` (the page's analytics event). `label` is the
 * button's accessible name; `words` its visible text, in the page's language. */
export function CopyButton({
  text,
  label,
  words = { copy: "Copy", copied: "Copied" },
  onCopied,
}: {
  text: string
  label: string
  words?: { copy: string; copied: string }
  onCopied?: () => void
}) {
  const [copied, setCopied] = useState(false)
  const copy = async (button: HTMLButtonElement) => {
    if (!(await copyToClipboard(text, { focus: button }))) return
    setCopied(true)
    onCopied?.()
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      aria-label={label}
      onClick={(event) => copy(event.currentTarget)}
      className="print:hidden"
    >
      {copied ? <Check /> : <Copy />}
      <span aria-live="polite">{copied ? words.copied : words.copy}</span>
    </Button>
  )
}
