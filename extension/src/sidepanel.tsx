import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"

import { client } from "@/client/client.gen"
import { Panel } from "./Panel"
import "./sidepanel.css"

// The same API as the website, so the extension shares its free-check limit (one a week).
client.setConfig({
  baseURL: import.meta.env.VITE_API_URL ?? "https://checkon.ca",
  withCredentials: true,
})

// Follow the browser's light or dark setting, like the website's "system" theme.
const dark = window.matchMedia("(prefers-color-scheme: dark)")
const applyTheme = () =>
  document.documentElement.classList.toggle("dark", dark.matches)
applyTheme()
dark.addEventListener("change", applyTheme)

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={new QueryClient()}>
      <Panel />
    </QueryClientProvider>
  </StrictMode>,
)
