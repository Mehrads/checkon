import {
  Archive,
  Building2,
  ChartColumn,
  Home,
  type LucideIcon,
  ScanSearch,
  Settings,
  Users,
} from "lucide-react"

import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { useWorkspaces } from "@/hooks/useWorkspace"

export type NavItem = {
  icon: LucideIcon
  title: string
  path: string
}

/** The account's pages: the rail on a computer, the menu on a phone. */
export function useNavItems(): NavItem[] {
  const { user } = useAuth()
  const { clients } = useWorkspaces(isLoggedIn())

  return [
    { icon: Home, title: "Checks", path: "/" },
    { icon: ScanSearch, title: "Careers page audit", path: "/audits" },
    {
      icon: Building2,
      title: clients ? "Client workspaces" : "Company profile",
      path: "/profile",
    },
    { icon: Archive, title: "Archive", path: "/archive" },
    ...(user?.is_superuser
      ? [
          { icon: ChartColumn, title: "Stats", path: "/stats" },
          { icon: Users, title: "Admin", path: "/admin" },
        ]
      : []),
    { icon: Settings, title: "Settings", path: "/settings" },
  ]
}

export function isActivePath(path: string, currentPath: string): boolean {
  return path === "/" ? currentPath === "/" : currentPath.startsWith(path)
}
