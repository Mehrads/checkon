import { Link } from "@tanstack/react-router"
import { FilePen } from "lucide-react"
import type { ReactNode } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Brand, SiteFooter } from "./Landing"

export const LEGAL_EMAIL = "info@checkon.ca"

/** The privacy policy and the terms: a header, the draft notice, then the sections. */
export function LegalPage({
  eyebrow,
  title,
  drafted,
  draftNote,
  children,
}: {
  eyebrow: string
  title: string
  drafted: string
  draftNote: string
  children: ReactNode
}) {
  return (
    <div className="site min-h-svh bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Brand href="/check" />
          <div className="flex items-center gap-2">
            <Appearance />
            <Button asChild size="sm">
              <Link to="/check">Check a posting</Link>
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-10 px-4 py-16 sm:px-6 sm:py-20">
        <div className="space-y-3">
          <p className="text-sm font-medium text-primary">{eyebrow}</p>
          <h1 className="text-4xl font-semibold tracking-tight text-balance">
            {title}
          </h1>
          <p className="text-muted-foreground">Draft of {drafted}</p>
        </div>

        <Alert role="note" className="border-primary/40 bg-primary/5">
          <FilePen aria-hidden="true" />
          <AlertTitle>Draft for legal review</AlertTitle>
          <AlertDescription>{draftNote}</AlertDescription>
        </Alert>

        {children}
      </main>
      <SiteFooter home="/check" />
    </div>
  )
}

export function Part({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      <div className="space-y-3 text-muted-foreground [&_strong]:font-medium [&_strong]:text-foreground">
        {children}
      </div>
    </section>
  )
}

export function List({ children }: { children: ReactNode }) {
  return (
    <ul className="list-disc space-y-2 pl-5 marker:text-primary">{children}</ul>
  )
}

export function Code({ children }: { children: ReactNode }) {
  return (
    <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em] text-foreground">
      {children}
    </code>
  )
}

export const Mail = () => (
  <a
    href={`mailto:${LEGAL_EMAIL}`}
    className="text-primary underline-offset-4 hover:underline"
  >
    {LEGAL_EMAIL}
  </a>
)

export function PageLink({
  to,
  children,
}: {
  to: string
  children: ReactNode
}) {
  return (
    <Link to={to} className="text-primary underline-offset-4 hover:underline">
      {children}
    </Link>
  )
}
