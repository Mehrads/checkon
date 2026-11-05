import { Link, useNavigate } from "@tanstack/react-router"
import { LogOut, Settings } from "lucide-react"
import { type FormEvent, useState } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { WorkspaceSwitcher } from "@/components/Profile/WorkspaceSwitcher"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { useWorkspaces } from "@/hooks/useWorkspace"
import { cn } from "@/lib/utils"
import { getInitials } from "@/utils"
import { RailMenu } from "./Rail"

/** The avatar and greeting, which open the account menu. `compact`: the avatar alone. */
function UserMenu({ compact }: { compact: boolean }) {
  const { user, logout } = useAuth()
  if (!user) return null
  const name = user.full_name?.trim()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        data-testid="user-menu"
        aria-label="Account menu"
        className="flex min-w-0 items-center gap-2 rounded-full pr-2 outline-none focus-visible:ring-2 focus-visible:ring-white/80"
      >
        <Avatar className="size-8">
          <AvatarFallback className="bg-white/20 text-xs font-medium text-white">
            {getInitials(name || "User")}
          </AvatarFallback>
        </Avatar>
        <span
          className={cn(
            "truncate text-sm font-medium",
            compact && "max-sm:sr-only",
          )}
        >
          Welcome{name ? `, ${name.split(" ")[0]}` : ""}
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="min-w-56 rounded-2xl" align="start">
        <DropdownMenuLabel className="font-normal">
          <p className="truncate text-sm font-medium">{name}</p>
          <p className="truncate text-xs text-muted-foreground">{user.email}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <Link to="/settings">
          <DropdownMenuItem>
            <Settings />
            User Settings
          </DropdownMenuItem>
        </Link>
        <DropdownMenuItem onClick={() => logout()}>
          <LogOut />
          Log Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

/** The bar's middle: paste a posting's link from any page and it opens in the checker, ready to check. */
function QuickCheck() {
  const navigate = useNavigate()
  const [url, setUrl] = useState("")
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!url.trim()) return
    navigate({ to: "/", search: { url: url.trim() } })
    setUrl("")
  }
  return (
    <form
      onSubmit={submit}
      className="mx-auto hidden w-full max-w-md items-center gap-2 rounded-full px-3 focus-within:bg-white/10 lg:flex"
    >
      <span className="orb size-4.5 shrink-0 rounded-full" aria-hidden="true" />
      <input
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        aria-label="A posting's link to check"
        placeholder="Paste a posting's link to check it…"
        className="h-8 w-full min-w-0 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
      />
    </form>
  )
}

/** The thin bar across the top: who's signed in, a quick way into a check, the client (once the account has
 * several workspaces), the theme. */
export function TopBar() {
  const { workspaces, current, clients } = useWorkspaces(isLoggedIn())
  const client = clients && current ? current : undefined
  return (
    <header className="glass-bar absolute inset-x-2 top-2 z-20 flex h-12 items-center gap-1.5 rounded-full px-2 md:inset-x-(--shell-x) md:top-3">
      <RailMenu className="md:hidden" />
      <Logo variant="icon" className="hidden text-base md:flex" />
      <UserMenu compact={Boolean(client)} />
      <div className="flex min-w-0 flex-1 items-center">
        <QuickCheck />
      </div>
      {client && (
        <div className="flex min-w-0 items-center gap-2 text-sm">
          <span className="hidden text-muted-foreground sm:inline">Client</span>
          <WorkspaceSwitcher
            workspaces={workspaces}
            current={client}
            className="rounded-full"
          />
          <Link
            to="/profile"
            className="hidden text-muted-foreground underline-offset-4 hover:text-foreground hover:underline sm:inline"
          >
            Manage
          </Link>
        </div>
      )}
      <Appearance className="ml-1 size-8 rounded-full border-0 bg-solid text-on-solid hover:bg-solid/85 hover:text-on-solid dark:bg-solid dark:hover:bg-solid/85" />
    </header>
  )
}
