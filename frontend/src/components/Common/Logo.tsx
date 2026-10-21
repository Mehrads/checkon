import { Link } from "@tanstack/react-router"
import { FileCheck2 } from "lucide-react"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

// Sized in em so a larger text size (e.g. `text-4xl`) scales the whole mark.
export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content = (
    <span
      className={cn(
        "flex items-center gap-2 text-lg font-semibold tracking-tight",
        className,
      )}
    >
      <span className="flex size-[1.75em] shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <FileCheck2 className="size-[1em]" aria-hidden="true" />
      </span>
      <span
        className={cn(
          variant === "icon" && "sr-only",
          variant === "responsive" && "group-data-[collapsible=icon]:sr-only",
        )}
      >
        Check<span className="text-primary">ON</span>
      </span>
    </span>
  )

  if (!asLink) {
    return content
  }

  return <Link to="/">{content}</Link>
}
