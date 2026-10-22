import { type ReactNode, useState } from "react"

import type { WorkspacePublic, WorkspaceUpdate } from "@/client"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { apiMessage } from "@/hooks/useBilling"
import useCustomToast from "@/hooks/useCustomToast"
import { useSaveProfile } from "@/hooks/useWorkspace"
import { formatDay } from "../Billing/UsageMeter"

type Size = "number" | "at_least" | "fewer" | "unknown"
type Choice = "yes" | "no" | "ask"

function sizeOf(profile: WorkspacePublic): Size {
  if (profile.headcount !== null) return "number"
  if (profile.meets_headcount_threshold === null) return "unknown"
  return profile.meets_headcount_threshold ? "at_least" : "fewer"
}

function choiceOf(value: boolean | null): Choice {
  return value === null ? "ask" : value ? "yes" : "no"
}

function Option({
  id,
  value,
  children,
}: {
  id: string
  value: string
  children: ReactNode
}) {
  return (
    <div className="flex items-start gap-3 rounded-lg border p-3 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5">
      <RadioGroupItem id={id} value={value} className="mt-0.5" />
      <Label htmlFor={id} className="block leading-snug font-normal">
        {children}
      </Label>
    </div>
  )
}

function Field({
  title,
  help,
  children,
}: {
  title: string
  help: ReactNode
  children: ReactNode
}) {
  return (
    <fieldset className="grid gap-3 border-t pt-6 first:border-t-0 first:pt-0 md:grid-cols-[minmax(0,18rem)_1fr] md:gap-8">
      <div>
        <legend className="text-sm font-semibold">{title}</legend>
        <p className="mt-1 text-sm text-muted-foreground">{help}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </fieldset>
  )
}

/** The company profile: who the employer is, its size in Ontario, AI in hiring, and the wording style. */
export function ProfileForm({ profile }: { profile: WorkspacePublic }) {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const save = useSaveProfile()
  const threshold = profile.headcount_threshold
  const [employer, setEmployer] = useState(profile.employer_name ?? "")
  const [size, setSize] = useState<Size>(sizeOf(profile))
  const [headcount, setHeadcount] = useState(
    profile.headcount === null ? "" : String(profile.headcount),
  )
  const [ai, setAi] = useState<Choice>(choiceOf(profile.uses_ai_in_hiring))
  const [wording, setWording] = useState(profile.wording)
  const count = Number(headcount)
  const countValid =
    size !== "number" || (headcount !== "" && Number.isInteger(count))

  const submit = () => {
    const body: WorkspaceUpdate = {
      employer_name: employer,
      headcount: size === "number" ? count : null,
      meets_headcount_threshold:
        size === "at_least" ? true : size === "fewer" ? false : null,
      uses_ai_in_hiring: ai === "ask" ? null : ai === "yes",
      wording,
    }
    save.mutate(
      { id: profile.id, ...body },
      {
        onSuccess: () =>
          showSuccessToast("Your next checks start from this profile."),
        onError: (error) =>
          showErrorToast(apiMessage(error, "We couldn't save your profile.")),
      },
    )
  }

  return (
    <form
      className="space-y-6 rounded-xl border bg-card p-5 shadow-sm sm:p-6"
      onSubmit={(event) => {
        event.preventDefault()
        if (countValid) submit()
      }}
    >
      <Field
        title="Employer name"
        help="As it appears on your postings. Without a headcount below, we look this name up to estimate your size."
      >
        <Input
          aria-label="Employer name"
          value={employer}
          maxLength={255}
          onChange={(event) => setEmployer(event.target.value)}
          placeholder="Acme Inc."
        />
      </Field>

      <Field
        title="Employees in Ontario"
        help="Count everyone you employ in Ontario on the day a job is posted, including part-time and casual staff and anyone on leave."
      >
        <RadioGroup value={size} onValueChange={(v) => setSize(v as Size)}>
          <Option id="size-number" value="number">
            <span className="flex flex-wrap items-center gap-2">
              The exact number
              <Input
                type="number"
                min={0}
                step={1}
                inputMode="numeric"
                aria-label="Number of employees in Ontario"
                value={headcount}
                onFocus={() => setSize("number")}
                onChange={(event) => {
                  setHeadcount(event.target.value)
                  setSize("number")
                }}
                className="h-8 w-28"
              />
            </span>
          </Option>
          <Option id="size-at-least" value="at_least">
            {threshold} or more
          </Option>
          <Option id="size-fewer" value="fewer">
            Fewer than {threshold}
          </Option>
          <Option id="size-unknown" value="unknown">
            Not sure: estimate it from a web search for the employer
          </Option>
        </RadioGroup>
        {!countValid && (
          <p className="mt-2 text-sm text-destructive">
            Enter a whole number of employees.
          </p>
        )}
      </Field>

      <Field
        title="AI in hiring"
        help="Do you, or a recruiter acting for you, use AI to screen, assess or select applicants? This includes ATS auto-ranking, resume scoring and chat screening."
      >
        <RadioGroup value={ai} onValueChange={(v) => setAi(v as Choice)}>
          <Option id="ai-yes" value="yes">
            Yes: add a disclosure to postings that lack one
          </Option>
          <Option id="ai-no" value="no">
            No
          </Option>
          <Option id="ai-ask" value="ask">
            It depends on the job: ask me on each check
          </Option>
        </RadioGroup>
      </Field>

      <Field
        title="Wording"
        help="The style of the statements CheckON adds to a posting, such as the vacancy statement."
      >
        <RadioGroup
          value={wording}
          onValueChange={(v) => setWording(v as WorkspacePublic["wording"])}
        >
          {/* Examples from the wording library (backend/rulepacks/CA-ON/wording.yaml) */}
          <Option id="wording-formal" value="formal">
            Formal{" "}
            <span className="text-muted-foreground">
              "This posting is for an existing vacancy."
            </span>
          </Option>
          <Option id="wording-plain" value="plain">
            Plain{" "}
            <span className="text-muted-foreground">
              "This job is an existing vacancy."
            </span>
          </Option>
        </RadioGroup>
      </Field>

      <div className="flex flex-wrap items-center justify-end gap-3 border-t pt-6">
        {profile.updated_at && (
          <span className="text-xs text-muted-foreground">
            Last saved {formatDay(profile.updated_at)}
          </span>
        )}
        <LoadingButton type="submit" loading={save.isPending}>
          Save profile
        </LoadingButton>
      </div>
    </form>
  )
}
