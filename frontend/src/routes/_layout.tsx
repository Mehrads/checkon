import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"

import { Shell } from "@/components/Shell/Shell"
import { isLoggedIn } from "@/hooks/useAuth"
import { noindex } from "@/lib/seo"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  head: noindex,
  beforeLoad: async ({ location }) => {
    // v1 has no sign-up: visitors land on the free check; /login still works directly. A link to another account
    // page (the extension's "Open it", say) logs in first, then comes back to it.
    if (!isLoggedIn()) {
      throw location.pathname === "/"
        ? redirect({ to: "/check" })
        : redirect({ to: "/login", search: { redirect: location.href } })
    }
  },
})

function Layout() {
  return (
    <Shell>
      <Outlet />
    </Shell>
  )
}
