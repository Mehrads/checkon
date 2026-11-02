import type { ReactNode } from "react"

/** The top of a signed-in page: the parent page's name when it has one, the title, a lead line. */
export function PageHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string
  title: string
  children?: ReactNode
}) {
  return (
    <div className="min-w-0">
      {eyebrow && (
        <p className="mb-1 text-sm font-medium text-muted-foreground">
          {eyebrow}
        </p>
      )}
      <h1 className="font-display text-2xl leading-tight font-medium sm:text-3xl">
        {title}
      </h1>
      {children && (
        <p className="mt-1 truncate text-sm text-muted-foreground">
          {children}
        </p>
      )}
    </div>
  )
}
