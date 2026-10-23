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

const handleApiError = (error: Error) => {
  if (!(error instanceof AxiosError)) return
  const status = error.response?.status
  if (status === 401 || status === 403) {
    localStorage.removeItem("access_token")
    // An expired sign-in (the API's 403 "Could not validate credentials") comes back to this page after logging
    // in again; a page the plan doesn't include doesn't.
    const expired =
      status === 401 ||
      error.response?.data?.detail === "Could not validate credentials"
    const page = window.location.pathname + window.location.search
    window.location.href =
      expired && window.location.pathname !== "/login"
        ? `/login?${new URLSearchParams({ redirect: page })}`
        : "/login"
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

const router = createRouter({ routeTree })
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
