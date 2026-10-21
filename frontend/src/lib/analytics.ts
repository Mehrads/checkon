// Umami Cloud: cookieless page views and a few named events, so no consent banner is needed.
// Off unless VITE_UMAMI_WEBSITE_ID is set, and it only counts visits on the public domain,
// so local work and the run.app address stay out of the numbers.

const WEBSITE_ID = import.meta.env.VITE_UMAMI_WEBSITE_ID as string | undefined
const DOMAINS = "checkon.ca"

type EventData = Record<string, string | number>

declare global {
  interface Window {
    umami?: { track: (event: string, data?: EventData) => void }
  }
}

/** Load the script once; call it from public pages only, so the admin area isn't counted. */
export function loadAnalytics() {
  if (!WEBSITE_ID || document.getElementById("umami")) return
  const script = document.createElement("script")
  script.id = "umami"
  script.defer = true
  script.src = "https://cloud.umami.is/script.js"
  script.dataset.websiteId = WEBSITE_ID
  script.dataset.domains = DOMAINS
  document.head.appendChild(script)
}

export function track(event: string, data?: EventData) {
  window.umami?.track(event, data)
}
