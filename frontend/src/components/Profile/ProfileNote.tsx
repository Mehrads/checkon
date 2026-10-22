import { Building2, Check } from "lucide-react"
import type { ReactNode } from "react"

import type { Answers, ProfileUpdate, WorkspacePublic } from "@/client"
import { LoadingButton } from "@/components/ui/loading-button"
import { useSaveProfile } from "@/hooks/useWorkspace"

// Shared by the website's checker and the extension's side panel, so links come in as rendered nodes.

/** The profile's facts in a few words each, for the line above the check. */
export function profileFacts(profile: WorkspacePublic): string[] {
  const threshold = profile.headcount_threshold
  const facts: string[] = []
  if (profile.employer_name) facts.push(profile.employer_name)
  if (profile.headcount !== null)
    facts.push(`${profile.headcount.toLocaleString()} employees in Ontario`)
  else if (profile.meets_headcount_threshold !== null)
    facts.push(
      profile.meets_headcount_threshold
        ? `${threshold} or more employees in Ontario`
        : `Fewer than ${threshold} employees in Ontario`,
    )
  if (profile.uses_ai_in_hiring !== null)
    facts.push(
      profile.uses_ai_in_hiring ? "Uses AI in hiring" : "No AI in hiring",
    )
  facts.push(profile.wording === "plain" ? "Plain wording" : "Formal wording")
  return facts
}

/** "Using your company profile" with its facts, or an invitation to set one up; `edit` is the link. */
export function ProfileNote({
  profile,
  edit,
}: {
  profile: WorkspacePublic
  edit: (label: string) => ReactNode
}) {
  return (
    <p className="flex items-start gap-2 rounded-lg bg-muted/60 px-3 py-2 text-xs text-muted-foreground">
      <Building2
        className="mt-px size-4 shrink-0 text-primary"
        aria-hidden="true"
      />
      {profile.updated_at ? (
        <span>
          <span className="font-medium text-foreground">
            Using your company profile:
          </span>{" "}
          {profileFacts(profile).join(" · ")}. {edit("Edit")}
        </span>
      ) : (
        <span>
          Save your company's details once and checks stop asking for them.{" "}
          {edit("Set up your company profile")}
        </span>
      )}
    </p>
  )
}

/** The answers a company profile can hold: facts about the company, not this posting. */
export function profileAnswers(answers: Answers): ProfileUpdate {
  const picked: ProfileUpdate = {}
  if (typeof answers.uses_ai_in_hiring === "boolean")
    picked.uses_ai_in_hiring = answers.uses_ai_in_hiring
  if (typeof answers.meets_headcount_threshold === "boolean")
    picked.meets_headcount_threshold = answers.meets_headcount_threshold
  return picked
}

function describe(answers: ProfileUpdate, threshold: number): string[] {
  const lines: string[] = []
  if (answers.uses_ai_in_hiring !== undefined)
    lines.push(
      answers.uses_ai_in_hiring
        ? "You, or a recruiter acting for you, use AI to screen, assess or select applicants."
        : "You don't use AI to screen, assess or select applicants.",
    )
  if (answers.meets_headcount_threshold !== undefined)
    lines.push(
      answers.meets_headcount_threshold
        ? `You have ${threshold} or more employees in Ontario.`
        : `You have fewer than ${threshold} employees in Ontario.`,
    )
  return lines
}

/** After a question about the company is answered: keep the answer for every check. */
export function SaveToProfile({
  workspaceId,
  threshold,
  answers,
}: {
  workspaceId: string
  threshold: number
  answers: ProfileUpdate
}) {
  const save = useSaveProfile()
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-dashed bg-card p-4 text-sm">
      <div className="min-w-0 flex-1 basis-60">
        <p className="font-medium">Use your answer for every check?</p>
        <p className="text-muted-foreground">
          {describe(answers, threshold).join(" ")}
        </p>
        {save.isError && (
          <p className="text-destructive">
            We couldn't save it to your profile. Try again.
          </p>
        )}
      </div>
      {save.isSuccess ? (
        <span className="flex items-center gap-1.5 font-medium">
          <Check className="size-4 text-primary" aria-hidden="true" />
          Saved to your company profile
        </span>
      ) : (
        <LoadingButton
          variant="outline"
          size="sm"
          loading={save.isPending}
          onClick={() => save.mutate({ id: workspaceId, ...answers })}
        >
          Save to my company profile
        </LoadingButton>
      )}
    </div>
  )
}
