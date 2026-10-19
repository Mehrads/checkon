import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import {
  ChecksService,
  type CustomRequestIn,
  type ResearchQuestion,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"

/** One short, optional question after each result (Research guide). */
export function ResearchQuestionCard({
  checkId,
  question,
}: {
  checkId: string
  question: ResearchQuestion
}) {
  const send = useMutation({
    mutationFn: (answer: string) =>
      ChecksService.answerResearch({
        body: { check_id: checkId, question_id: question.id, answer },
      }),
  })
  return (
    <Card>
      <CardHeader>
        <CardTitle>One quick question</CardTitle>
        <CardDescription>
          Optional. It helps us decide what to build.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm">{question.text}</p>
        {send.isSuccess ? (
          <p className="text-sm text-muted-foreground">Thanks!</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {question.options.map((option) => (
              <Button
                key={option}
                size="sm"
                variant="outline"
                disabled={send.isPending}
                onClick={() => send.mutate(option)}
              >
                {option}
              </Button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

const EMPTY = { hr_system: "", postings_per_month: "", wants: "", email: "" }

/** "Want this to run automatically on your HR system?" opens a short request form. */
export function RequestForm({
  checkId,
  startOpen = false,
}: {
  checkId?: string
  startOpen?: boolean
}) {
  const [open, setOpen] = useState(startOpen)
  const [form, setForm] = useState(EMPTY)
  const send = useMutation({
    mutationFn: (body: CustomRequestIn) =>
      ChecksService.requestCustomSolution({ body }),
  })
  const set = (key: keyof typeof EMPTY) => (value: string) =>
    setForm({ ...form, [key]: value })
  const complete = Object.values(form).every((value) => value.trim())

  return (
    <Card>
      <CardHeader>
        <CardTitle>Want this to run automatically on your HR system?</CardTitle>
        <CardDescription>
          Tell us what you use and we'll get back to you with a setup.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {send.isSuccess ? (
          <p className="text-sm">Thanks! We'll email you about your request.</p>
        ) : !open ? (
          <Button
            variant="outline"
            className="self-start"
            onClick={() => setOpen(true)}
          >
            Tell us about your setup
          </Button>
        ) : (
          <form
            className="flex flex-col gap-3"
            onSubmit={(event) => {
              event.preventDefault()
              send.mutate({ ...form, check_id: checkId })
            }}
          >
            <Field label="HR or recruiting system" id="hr_system">
              <Input
                id="hr_system"
                value={form.hr_system}
                onChange={(event) => set("hr_system")(event.target.value)}
                placeholder="For example BambooHR"
              />
            </Field>
            <Field label="Job postings a month" id="postings">
              <Input
                id="postings"
                value={form.postings_per_month}
                onChange={(event) =>
                  set("postings_per_month")(event.target.value)
                }
                placeholder="For example 10"
              />
            </Field>
            <Field label="What should run automatically?" id="wants">
              <textarea
                id="wants"
                value={form.wants}
                onChange={(event) => set("wants")(event.target.value)}
                className="min-h-20 w-full rounded-md border bg-transparent p-2 text-sm"
              />
            </Field>
            <Field label="Work email" id="email">
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={(event) => set("email")(event.target.value)}
              />
            </Field>
            {send.isError && (
              <p className="text-sm text-destructive">
                Check the email address and try again.
              </p>
            )}
            <LoadingButton
              type="submit"
              loading={send.isPending}
              disabled={!complete}
              className="self-start"
            >
              Send request
            </LoadingButton>
          </form>
        )}
      </CardContent>
    </Card>
  )
}

function Field({
  label,
  id,
  children,
}: {
  label: string
  id: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      {children}
    </div>
  )
}
