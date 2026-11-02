import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { AxiosError } from "axios"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { client } from "./client/client.gen"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import "@fontsource-variable/newsreader/wght.css"
import "@fontsource-variable/hanken-grotesk/wght.css"
import "./index.css"
import { routeTree } from "./routeTree.gen"

client.setConfig({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  withCredentials: true,
  auth: () => localStorage.getItem("access_token") || "",
})

// The API's 403 for an expired or invalid token (backend/app/api/deps.py)
const BAD_TOKEN = "Could not validate credentials"

const handleApiError = (error: Error) => {
  if (!(error instanceof AxiosError)) return
  const { status, data } = error.response ?? {}
  // Only a sign-in that no longer works logs out. Other 403s, such as "The archive comes with a paid plan", are
  // the page's to show.
  if (status === 401 || (status === 403 && data?.detail === BAD_TOKEN)) {
    localStorage.removeItem("access_token")
    // Log in again, then come back to this page
    const page = window.location.pathname + window.location.search
    window.location.href =
      window.location.pathname === "/login"
        ? "/login"
        : `/login?${new URLSearchParams({ redirect: page })}`
  }
}
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

const router = createRouter({
  routeTree,
  // Back returns to where you were on the page; a new page starts at its top, in the app's panel too
  scrollRestoration: true,
  scrollToTopSelectors: ["#app-scroll"],
})
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

// The head tags index.html or a page rendered at build time carry for the first paint: the routes render their own
for (const tag of document.head.querySelectorAll("[data-static-head]"))
  tag.remove()

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
