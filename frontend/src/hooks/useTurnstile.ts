import { useCallback, useEffect, useRef, useState } from "react"

// Cloudflare Turnstile, rendered explicitly. It stays invisible unless Cloudflare needs an interaction.
const SCRIPT =
  "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"

interface TurnstileApi {
  render: (element: HTMLElement, options: Record<string, unknown>) => string
  reset: (widgetId?: string) => void
  remove: (widgetId?: string) => void
}

declare global {
  interface Window {
    turnstile?: TurnstileApi
  }
}

function loadScript(): Promise<TurnstileApi> {
  if (window.turnstile) return Promise.resolve(window.turnstile)
  return new Promise((resolve, reject) => {
    let script = document.querySelector<HTMLScriptElement>(
      `script[src="${SCRIPT}"]`,
    )
    if (!script) {
      script = document.createElement("script")
      script.src = SCRIPT
      script.async = true
      document.head.appendChild(script)
    }
    script.addEventListener("load", () =>
      window.turnstile
        ? resolve(window.turnstile)
        : reject(new Error("Turnstile")),
    )
    script.addEventListener("error", () => reject(new Error("Turnstile")))
  })
}

/** A token for the next free check; without a site key (local development) there is no widget. */
export function useTurnstile(siteKey: string | undefined) {
  const ref = useRef<HTMLDivElement>(null)
  const widget = useRef<string | undefined>(undefined)
  const [token, setToken] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!siteKey) return
    let cancelled = false
    loadScript()
      .then((turnstile) => {
        if (cancelled || !ref.current) return
        widget.current = turnstile.render(ref.current, {
          sitekey: siteKey,
          appearance: "interaction-only",
          callback: (value: string) => setToken(value),
          "expired-callback": () => setToken(null),
          "error-callback": () => setFailed(true),
        })
      })
      .catch(() => setFailed(true))
    return () => {
      cancelled = true
      if (widget.current) window.turnstile?.remove(widget.current)
    }
  }, [siteKey])

  const reset = useCallback(() => {
    setToken(null)
    if (widget.current) window.turnstile?.reset(widget.current)
  }, [])

  return { ref, token, reset, enabled: Boolean(siteKey), failed }
}
