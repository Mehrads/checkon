// source: https://usehooks-ts.com/react-hook/use-copy-to-clipboard, copying through lib/clipboard's fallback
import { useCallback, useState } from "react"
import { copyToClipboard } from "@/lib/clipboard"

type CopiedValue = string | null

type CopyFn = (text: string) => Promise<boolean>

export function useCopyToClipboard(): [CopiedValue, CopyFn] {
  const [copiedText, setCopiedText] = useState<CopiedValue>(null)

  const copy: CopyFn = useCallback(async (text) => {
    // The fallback selects a hidden copy of the text; the focus goes back to what had it (the button clicked)
    const focused = document.activeElement
    const done = await copyToClipboard(text, {
      focus: focused instanceof HTMLElement ? focused : undefined,
    })
    if (!done) {
      console.warn("Copy failed")
      setCopiedText(null)
      return false
    }

    setCopiedText(text)
    setTimeout(() => setCopiedText(null), 2000)
    return true
  }, [])

  return [copiedText, copy]
}
