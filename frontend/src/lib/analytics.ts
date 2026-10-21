// Umami Cloud: cookieless page views and a few named events, so no consent banner is needed.
// Off unless VITE_UMAMI_WEBSITE_ID is set, and it only counts visits on the public domain,
// so local work and the run.app address stay out of the numbers.
//
// Analytics must never break the check: ad blockers often block the script, so `track` only calls
// Umami once it has really loaded, and swallows any error. (Don't give the script an id: browsers
// expose element ids as globals, so `window.umami` would become the script tag itself.)

const WEBSITE_ID = import.meta.env.VITE_UMAMI_WEBSITE_ID as string | undefined
const DOMAINS = "checkon.ca"

type EventData = Record<string, string | number>

declare global {
  interface Window {
    umami?: { track?: (event: string, data?: EventData) => void }
  }
}

let loaded = false

/** Load the script once; call it from public pages only, so the admin area isn't counted. */
export function loadAnalytics() {
  if (!WEBSITE_ID || loaded) return
  loaded = true
  const script = document.createElement("script")
  script.defer = true
  script.src = "https://cloud.umami.is/script.js"
  script.dataset.websiteId = WEBSITE_ID
  script.dataset.domains = DOMAINS
  document.head.appendChild(script)
}

export function track(event: string, data?: EventData) {
  try {
    const umami = window.umami
    if (typeof umami?.track === "function") umami.track(event, data)
  } catch {
    // Never let analytics interrupt the check.
  }
}
