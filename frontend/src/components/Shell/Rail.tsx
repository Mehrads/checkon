import { Link, useRouterState } from "@tanstack/react-router"
import { Menu } from "lucide-react"
import { useState } from "react"

import { Logo } from "@/components/Common/Logo"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { isActivePath, useNavItems } from "./nav"

/** The pages, as round icons on the panel's left edge; each one names itself on hover and on keyboard focus. */
export function Rail() {
  const items = useNavItems()
  const currentPath = useRouterState({ select: (s) => s.location.pathname })
  return (
    <nav
      aria-label="Account pages"
      className="glass-bar absolute top-28 left-[calc(var(--shell-x)-1.375rem)] z-20 hidden max-h-[calc(100%-11rem)] flex-col items-center gap-1 overflow-y-auto rounded-full p-1 no-scrollbar md:flex"
    >
      {items.map((item) => {
        const active = isActivePath(item.path, currentPath)
        return (
          <Tooltip key={item.path}>
            <TooltipTrigger asChild>
              <Link
                to={item.path}
                aria-label={item.title}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex size-9 shrink-0 items-center justify-center rounded-full outline-none transition-colors focus-visible:ring-2 focus-visible:ring-white/80",
                  active
                    ? "bg-solid text-on-solid shadow-sm"
                    : "text-muted-foreground hover:bg-white/15 hover:text-foreground",
                )}
              >
                <item.icon className="size-4.5" aria-hidden="true" />
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={10}>
              {item.title}
            </TooltipContent>
          </Tooltip>
        )
      })}
    </nav>
  )
}

/** A phone has no room for the rail: the same pages, with their names, in a menu. */
export function RailMenu({ className }: { className?: string }) {
  const items = useNavItems()
  const currentPath = useRouterState({ select: (s) => s.location.pathname })
  const [open, setOpen] = useState(false)
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Open the menu"
          className={cn("shrink-0 rounded-full", className)}
        >
          <Menu aria-hidden="true" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-72 gap-0 rounded-r-3xl p-4">
        <SheetTitle className="sr-only">Account pages</SheetTitle>
        <Logo />
        <nav aria-label="Account pages" className="mt-6 flex flex-col gap-1">
          {items.map((item) => {
            const active = isActivePath(item.path, currentPath)
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setOpen(false)}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-full px-4 py-2.5 text-sm font-medium",
                  active
                    ? "bg-foreground text-background"
                    : "text-foreground hover:bg-muted",
                )}
              >
                <item.icon className="size-4.5" aria-hidden="true" />
                {item.title}
              </Link>
            )
          })}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
