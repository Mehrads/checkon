import { useMutation } from "@tanstack/react-query"
import { Mail } from "lucide-react"
import { useState } from "react"

import { ChecksService, type ContactIn } from "@/client"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import { track } from "@/lib/analytics"
import { cn } from "@/lib/utils"

type Interest = ContactIn["interest"]

const INTERESTS: { value: Interest; label: string }[] = [
  { value: "custom", label: "Custom setup" },
  { value: "other", label: "Something else" },
]

/** Shown beside the form when the site's operator sets one (VITE_CONTACT_EMAIL); otherwise the form alone. */
export const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL || undefined

const EMPTY = { name: "", email: "", company: "", message: "" }

export function ContactForm() {
  const [interest, setInterest] = useState<Interest>("other")
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
        <p className="font-medium">Thanks, your message was sent.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          The reply will go to {form.email}.
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
              onClick={() => setInterest(option.value)}
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
          placeholder="Your question, or what you'd like set up…"
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
