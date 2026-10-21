import { useMutation } from "@tanstack/react-query"
import { Mail } from "lucide-react"
import { createContext, type ReactNode, useContext, useState } from "react"

import { ChecksService, type ContactIn } from "@/client"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import { track } from "@/lib/analytics"
import { cn } from "@/lib/utils"

export type Interest = ContactIn["interest"]

const INTERESTS: { value: Interest; label: string }[] = [
  { value: "starter", label: "Starter" },
  { value: "agency", label: "Agency" },
  { value: "custom", label: "Custom setup" },
  { value: "other", label: "Something else" },
]

export const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL as
  | string
  | undefined

// Pricing buttons preset what the message is about, then scroll to the form.
const ContactContext = createContext<{
  interest: Interest
  contactAbout: (interest: Interest) => void
}>({ interest: "other", contactAbout: () => {} })

export function ContactProvider({ children }: { children: ReactNode }) {
  const [interest, setInterest] = useState<Interest>("other")
  const contactAbout = (next: Interest) => {
    setInterest(next)
    document
      .getElementById("contact")
      ?.scrollIntoView({ behavior: "smooth", block: "start" })
  }
  return (
    <ContactContext.Provider value={{ interest, contactAbout }}>
      {children}
    </ContactContext.Provider>
  )
}

export const useContact = () => useContext(ContactContext)

const EMPTY = { name: "", email: "", company: "", message: "" }

export function ContactForm() {
  const { interest, contactAbout } = useContact()
  const [form, setForm] = useState(EMPTY)
  const send = useMutation({
    mutationFn: (body: ContactIn) => ChecksService.contact({ body }),
    onSuccess: (_, body) => track("contact", { interest: body.interest }),
  })
  const set =
    (key: keyof typeof EMPTY) => (event: { target: { value: string } }) =>
      setForm({ ...form, [key]: event.target.value })
  const ready = form.name.trim() && form.email.trim() && form.message.trim()

  if (send.isSuccess) {
    return (
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <p className="font-medium">Thanks, we got your message.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          We'll reply to {form.email} soon.
        </p>
      </div>
    )
  }

  return (
    <form
      className="space-y-4 rounded-xl border bg-card p-6 shadow-sm"
      onSubmit={(event) => {
        event.preventDefault()
        send.mutate({
          name: form.name,
          email: form.email,
          company: form.company || null,
          interest,
          message: form.message,
        })
      }}
    >
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">
          What are you interested in?
        </legend>
        <div className="flex flex-wrap gap-2">
          {INTERESTS.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-pressed={interest === option.value}
              onClick={() => contactAbout(option.value)}
              className={cn(
                "rounded-md border px-3 py-1.5 text-sm transition-colors hover:bg-accent",
                interest === option.value &&
                  "border-primary bg-primary text-primary-foreground hover:bg-primary/90",
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="contact-name">Name</Label>
          <Input
            id="contact-name"
            value={form.name}
            onChange={set("name")}
            autoComplete="name"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="contact-email">Work email</Label>
          <Input
            id="contact-email"
            type="email"
            value={form.email}
            onChange={set("email")}
            autoComplete="email"
          />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="contact-company">Company (optional)</Label>
        <Input
          id="contact-company"
          value={form.company}
          onChange={set("company")}
          autoComplete="organization"
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="contact-message">How can we help?</Label>
        <textarea
          id="contact-message"
          value={form.message}
          onChange={set("message")}
          maxLength={2000}
          placeholder="How many postings a month, which HR system you use, what you'd like automated…"
          className="min-h-28 w-full rounded-md border bg-transparent p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        />
      </div>
      {send.isError && (
        <p className="text-sm text-destructive">
          We couldn't send that. Check your email address and try again.
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <LoadingButton type="submit" loading={send.isPending} disabled={!ready}>
          Send message
        </LoadingButton>
        {CONTACT_EMAIL && (
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <Mail className="size-4" aria-hidden="true" /> Or email{" "}
            {CONTACT_EMAIL}
          </a>
        )}
      </div>
    </form>
  )
}
