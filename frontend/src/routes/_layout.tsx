import { createFileRoute, Link, Outlet, redirect } from "@tanstack/react-router"

import { Footer } from "@/components/Common/Footer"
import { WorkspaceSwitcher } from "@/components/Profile/WorkspaceSwitcher"
import AppSidebar from "@/components/Sidebar/AppSidebar"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { isLoggedIn } from "@/hooks/useAuth"
import { useBilling } from "@/hooks/useBilling"
import { useWorkspaces } from "@/hooks/useWorkspace"
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

/** Agency: the client whose company profile checks use, on every page of the account. */
function ClientSwitcher() {
  const { data: billing } = useBilling()
  const { workspaces, current, canCreate } = useWorkspaces(
    Boolean(billing?.plan),
  )
  if (!canCreate || !current) return null
  return (
    <div className="ml-auto flex min-w-0 items-center gap-2 text-sm">
      <span className="hidden text-muted-foreground sm:inline">Client</span>
      <WorkspaceSwitcher workspaces={workspaces} current={current} />
      <Link
        to="/profile"
        className="hidden text-muted-foreground underline-offset-4 hover:text-foreground hover:underline sm:inline"
      >
        Manage
      </Link>
    </div>
  )
}

function Layout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="min-w-0">
        <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
          <SidebarTrigger className="-ml-1 text-muted-foreground" />
          <ClientSwitcher />
        </header>
        <main className="flex-1 p-6 md:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
        <Footer />
      </SidebarInset>
    </SidebarProvider>
  )
}
