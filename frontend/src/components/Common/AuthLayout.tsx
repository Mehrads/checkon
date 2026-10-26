import { Check } from "lucide-react"
import type { ReactNode } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { Footer } from "./Footer"

interface AuthLayoutProps {
  children: ReactNode
}

const INCLUDED = [
  "Your checks for the month, on checkon.ca",
  "The date, job title and result of every check",
  "Reports on your job board, kept in one place",
]

/** Log-in, password and welcome pages: the brand panel on wide screens, the form beside it. */
export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="grid min-h-svh bg-background lg:grid-cols-[1fr_1.1fr]">
      <aside className="auth-panel relative hidden flex-col justify-between p-10 text-deep-foreground lg:flex xl:p-14 [--primary-foreground:#0a1f1c] [--primary:var(--deep-accent)]">
        <a href="/check" className="w-fit">
          <Logo asLink={false} className="text-xl" />
        </a>
        <div className="max-w-md">
          <p className="flex items-center gap-3 text-sm font-medium text-deep-muted">
            <span className="h-px w-8 bg-deep-accent" aria-hidden="true" />
            Your CheckON account
          </p>
          <p className="mt-6 font-display text-5xl leading-[1.04] font-medium tracking-[-0.02em] text-balance">
            Every posting checked{" "}
            <span className="text-deep-accent">before it goes live.</span>
          </p>
          <ul className="mt-8 space-y-3 border-t border-white/15 pt-6 text-sm text-deep-muted">
            {INCLUDED.map((line) => (
              <li key={line} className="flex gap-2.5">
                <Check
                  className="mt-0.5 size-4 shrink-0 text-deep-accent"
                  aria-hidden="true"
                />
                {line}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-deep-muted">
          Ontario job posting compliance. Not legal advice.
        </p>
      </aside>
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex items-center justify-between">
          <a href="/check" className="lg:invisible">
            <Logo asLink={false} />
          </a>
          <Appearance />
        </div>
        <div className="flex flex-1 items-center justify-center py-8">
          <div className="w-full max-w-sm">{children}</div>
        </div>
        <Footer />
      </div>
    </div>
  )
}

/** The display-type heading and short lead at the top of each auth form. */
export function AuthHeading({
  title,
  children,
}: {
  title: string
  children?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-2">
      <h1 className="font-display text-[2rem] leading-tight font-medium tracking-[-0.015em]">
        {title}
      </h1>
      {children && <p className="text-sm text-muted-foreground">{children}</p>}
    </div>
  )
}
