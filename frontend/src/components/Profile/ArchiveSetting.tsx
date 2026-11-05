import { Link } from "@tanstack/react-router"

import type { WorkspacePublic } from "@/client"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { useSaveProfile } from "@/hooks/useWorkspace"
import { apiMessage } from "@/lib/api"

/** The archive switch for one workspace (PRD FR11): off until the user turns it on. */
export function ArchiveSetting({
  profile,
  client,
}: {
  profile: WorkspacePublic
  /** With client workspaces: say whose postings are kept. */
  client: boolean
}) {
  const { showErrorToast } = useCustomToast()
  const save = useSaveProfile()
  const on = save.isPending
    ? Boolean(save.variables?.archive_postings)
    : profile.archive_postings
  const id = `archive-${profile.id}`

  return (
    <section className="space-y-3 rounded-xl border bg-card p-5 shadow-sm sm:p-6">
      <div>
        <h2 className="text-sm font-semibold">Archive of approved postings</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Ontario employers keep a copy of each posting, and its application
          form, for 3 years after it comes down. With the archive on, CheckON
          keeps a dated copy of each posting you apply fixes to, then deletes it
          3 years after the day you mark it taken down.
        </p>
      </div>
      <div className="flex items-start gap-3 rounded-lg border p-3 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5">
        <Checkbox
          id={id}
          checked={on}
          disabled={save.isPending}
          className="mt-0.5"
          onCheckedChange={(checked) =>
            save.mutate(
              { id: profile.id, archive_postings: checked === true },
              {
                onError: (error) =>
                  showErrorToast(
                    apiMessage(
                      error,
                      "We couldn't change the archive setting.",
                    ),
                  ),
              },
            )
          }
        />
        <Label htmlFor={id} className="block leading-snug font-normal">
          Keep the postings I apply fixes to
          {client ? ` for ${profile.name}` : ""}
          <span className="mt-0.5 block text-xs text-muted-foreground">
            Turning it off stops new saves. What's saved stays in the{" "}
            <Link to="/archive" className="underline underline-offset-4">
              archive
            </Link>{" "}
            until it's deleted.
          </span>
        </Label>
      </div>
    </section>
  )
}
