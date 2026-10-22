import type { ReactNode } from "react"

/** The top of a signed-in page: a short rule and label, the title in the display face, a lead line. */
export function PageHeading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string
  title: string
  children?: ReactNode
}) {
  return (
    <div className="min-w-0">
      <p className="flex items-center gap-3 text-sm font-medium text-muted-foreground">
        <span className="h-px w-8 bg-brand" aria-hidden="true" />
        {eyebrow}
      </p>
      <h1 className="mt-4 font-display text-4xl leading-tight font-medium tracking-[-0.015em]">
        {title}
      </h1>
      {children && (
        <p className="mt-1 truncate text-muted-foreground">{children}</p>
      )}
    </div>
  )
}
