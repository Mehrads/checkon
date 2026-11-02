import {
  Archive,
  Building2,
  ChartColumn,
  FileText,
  Home,
  type LucideIcon,
  Megaphone,
  ScanSearch,
  Settings,
  Users,
} from "lucide-react"

import useAuth from "@/hooks/useAuth"
import { isPaid, useBilling } from "@/hooks/useBilling"
import { useMyReports } from "@/hooks/useReports"
import { useWorkspaces } from "@/hooks/useWorkspace"

export type NavItem = {
  icon: LucideIcon
  title: string
  path: string
}

/** The account's pages: the rail on a computer, the menu on a phone. */
export function useNavItems(): NavItem[] {
  const { user } = useAuth()
  const { data: billing } = useBilling()
  const paid = isPaid(billing)
  const { canCreate } = useWorkspaces(paid)
  const { data: reports } = useMyReports()

  return [
    { icon: Home, title: "Checks", path: "/" },
    // The reports we sent that the customer saved, free account or not
    ...(reports?.length
      ? [{ icon: FileText, title: "Reports", path: "/reports" }]
      : []),
    ...(paid
      ? [
          { icon: ScanSearch, title: "Careers page audit", path: "/audits" },
          {
            icon: Building2,
            title: canCreate ? "Client workspaces" : "Company profile",
            path: "/profile",
          },
        ]
      : []),
    // Still there after the plan ends: the archive stays readable. A complimentary account has a plan but no
    // Stripe customer (has_billing).
    ...(paid || billing?.has_billing
      ? [{ icon: Archive, title: "Archive", path: "/archive" }]
      : []),
    ...(user?.is_superuser
      ? [
          { icon: ChartColumn, title: "Stats", path: "/stats" },
          { icon: Megaphone, title: "Outreach", path: "/outreach" },
          { icon: Users, title: "Admin", path: "/admin" },
        ]
      : []),
    { icon: Settings, title: "Settings", path: "/settings" },
  ]
}

export function isActivePath(path: string, currentPath: string): boolean {
  return path === "/" ? currentPath === "/" : currentPath.startsWith(path)
}
