import {
  Archive,
  Building2,
  ChartColumn,
  Home,
  ScanSearch,
  Users,
} from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { useBilling } from "@/hooks/useBilling"
import { useWorkspaces } from "@/hooks/useWorkspace"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [{ icon: Home, title: "Checks", path: "/" }]

export function AppSidebar() {
  const { user: currentUser } = useAuth()
  const { data: billing } = useBilling()
  const { canCreate } = useWorkspaces(Boolean(billing?.plan))

  const items = [
    ...baseItems,
    ...(billing?.plan
      ? [
          { icon: ScanSearch, title: "Careers page audit", path: "/audits" },
          {
            icon: Building2,
            title: canCreate ? "Client workspaces" : "Company profile",
            path: "/profile",
          },
        ]
      : []),
    // Still there after the plan ends: the archive stays readable
    ...(billing?.has_billing
      ? [{ icon: Archive, title: "Archive", path: "/archive" }]
      : []),
    ...(currentUser?.is_superuser
      ? [
          { icon: ChartColumn, title: "Stats", path: "/stats" },
          { icon: Users, title: "Admin", path: "/admin" },
        ]
      : []),
  ]

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
