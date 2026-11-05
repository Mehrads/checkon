import {
  focusManager,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"

import { client } from "@/client/client.gen"
import { Panel } from "./Panel"
import { API_URL } from "./site"
import { currentToken, loadToken } from "./token"
import "./sidepanel.css"

// The same API as the website, so the extension shares its free-check limit (one a week), and a
// signed-in user's checks are saved to their account.
client.setConfig({
  baseURL: API_URL,
  withCredentials: true,
  auth: currentToken,
})

// The panel stays visible while the user works in the window's tabs, so "visibilitychange" alone never
// refetches the account and the client list: also refetch when they come back to the panel, e.g. after adding a
// client or turning its archive on in the website's company profile.
focusManager.setEventListener((handleFocus) => {
  const listener = () => handleFocus()
  window.addEventListener("visibilitychange", listener)
  window.addEventListener("focus", listener)
  return () => {
    window.removeEventListener("visibilitychange", listener)
    window.removeEventListener("focus", listener)
  }
})

// Follow the browser's light or dark setting, like the website's "system" theme.
const dark = window.matchMedia("(prefers-color-scheme: dark)")
const applyTheme = () =>
  document.documentElement.classList.toggle("dark", dark.matches)
applyTheme()
dark.addEventListener("change", applyTheme)

loadToken().finally(() =>
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <QueryClientProvider client={new QueryClient()}>
        <Panel />
      </QueryClientProvider>
    </StrictMode>,
  ),
)
