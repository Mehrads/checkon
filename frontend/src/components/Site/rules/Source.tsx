import type { ReactNode } from "react"

/** A link to an official text, opened in a new tab. */
export function Source({
  href,
  children,
}: {
  href: string
  children: ReactNode
}) {
  return (
    <a
      href={href}
      className="text-primary underline-offset-4 hover:underline"
      rel="noreferrer"
      target="_blank"
    >
      {children}
    </a>
  )
}
