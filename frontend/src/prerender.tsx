/** The public pages as HTML, rendered at build time (scripts/prerender.ts) so search engines and visitors see the
 * page before any script runs. The app then renders over it in the browser, as it always has. Rendered signed out,
 * without the theme provider (it reads the browser's storage); index.html sets the theme before the first paint. */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  createMemoryHistory,
  createRouter,
  RouterProvider,
} from "@tanstack/react-router"
import { prerender } from "react-dom/static"

import { routeTree } from "./routeTree.gen"

/** Each page and the file it's written to, which the API serves at that path (backend/app/main.py). */
export const PAGES: Record<string, string> = {
  "/check": "check.html",
  "/privacy": "privacy.html",
  "/terms": "terms.html",
}

export async function render(path: string): Promise<string> {
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [path] }),
  })
  await router.load()
  const { prelude } = await prerender(
    <QueryClientProvider client={new QueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return await new Response(prelude).text()
}
