import { Archive, Pencil, Plus } from "lucide-react"
import { useState } from "react"

import type { WorkspacePublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { apiMessage } from "@/hooks/useBilling"
import useCustomToast from "@/hooks/useCustomToast"
import {
  useArchiveWorkspace,
  useCreateWorkspace,
  useSaveProfile,
  useSwitchWorkspace,
} from "@/hooks/useWorkspace"

function Rename({
  workspace,
  onDone,
}: {
  workspace: WorkspacePublic
  onDone: () => void
}) {
  const { showErrorToast } = useCustomToast()
  const save = useSaveProfile()
  const [name, setName] = useState(workspace.name)
  return (
    <form
      className="flex min-w-0 flex-1 flex-wrap items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        save.mutate(
          { id: workspace.id, name },
          {
            onSuccess: onDone,
            onError: (error) =>
              showErrorToast(apiMessage(error, "We couldn't rename it.")),
          },
        )
      }}
    >
      <Input
        aria-label="Workspace name"
        value={name}
        maxLength={255}
        autoFocus
        onFocus={(event) => event.target.select()}
        onChange={(event) => setName(event.target.value)}
        className="h-8 max-w-64"
      />
      <LoadingButton
        size="sm"
        type="submit"
        loading={save.isPending}
        disabled={!name.trim()}
      >
        Save
      </LoadingButton>
      <Button size="sm" variant="ghost" type="button" onClick={onDone}>
        Cancel
      </Button>
    </form>
  )
}

function ArchiveButton({
  workspace,
  disabled,
}: {
  workspace: WorkspacePublic
  disabled: boolean
}) {
  const [open, setOpen] = useState(false)
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const archive = useArchiveWorkspace()
  return (
    <>
      <Button
        size="sm"
        variant="ghost"
        disabled={disabled}
        title={disabled ? "Keep at least one workspace" : undefined}
        onClick={() => setOpen(true)}
      >
        <Archive />
        Archive
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Archive {workspace.name}?</DialogTitle>
            <DialogDescription>
              It leaves the switcher, and checks stop using its company profile.
              Its past checks stay in your history under its name.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <LoadingButton
              loading={archive.isPending}
              onClick={() =>
                archive.mutate(workspace.id, {
                  onSuccess: () => {
                    setOpen(false)
                    showSuccessToast(`${workspace.name} is archived.`)
                  },
                  onError: (error) =>
                    showErrorToast(
                      apiMessage(error, "We couldn't archive it."),
                    ),
                })
              }
            >
              Archive
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

function NewWorkspace() {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const create = useCreateWorkspace()
  const [name, setName] = useState("")
  return (
    <form
      className="flex flex-wrap items-center gap-2 border-t bg-muted/40 p-4"
      onSubmit={(event) => {
        event.preventDefault()
        create.mutate(name, {
          onSuccess: (workspace) => {
            setName("")
            showSuccessToast(
              `Checks now use ${workspace.name}. Fill in its profile below.`,
            )
          },
          onError: (error) =>
            showErrorToast(apiMessage(error, "We couldn't add it.")),
        })
      }}
    >
      <Input
        aria-label="New client's name"
        placeholder="New client's name"
        value={name}
        maxLength={255}
        onChange={(event) => setName(event.target.value)}
        className="h-9 max-w-72"
      />
      <LoadingButton
        type="submit"
        variant="outline"
        loading={create.isPending}
        disabled={!name.trim()}
      >
        <Plus />
        Add client workspace
      </LoadingButton>
    </form>
  )
}

/** Agency: a workspace per client, each with its own company profile. Checks use the one picked here or in
 * the switcher; the plan's checks are shared by all of them. */
export function Workspaces({
  workspaces,
  current,
}: {
  workspaces: WorkspacePublic[]
  current: WorkspacePublic
}) {
  const [renaming, setRenaming] = useState<string | null>(null)
  const switcher = useSwitchWorkspace()
  return (
    <section className="overflow-hidden rounded-xl border bg-card shadow-sm">
      <ul className="divide-y">
        {workspaces.map((workspace) => (
          <li
            key={workspace.id}
            className="flex flex-wrap items-center justify-between gap-2 px-4 py-3"
          >
            {renaming === workspace.id ? (
              <Rename workspace={workspace} onDone={() => setRenaming(null)} />
            ) : (
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <span className="truncate font-medium">{workspace.name}</span>
                {workspace.id === current.id ? (
                  <Badge variant="outline">Checks use this one</Badge>
                ) : (
                  <LoadingButton
                    size="sm"
                    variant="outline"
                    loading={
                      switcher.isPending && switcher.variables === workspace.id
                    }
                    disabled={switcher.isPending}
                    onClick={() => switcher.mutate(workspace.id)}
                  >
                    Use for checks
                  </LoadingButton>
                )}
              </div>
            )}
            {renaming !== workspace.id && (
              <div className="flex gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setRenaming(workspace.id)}
                >
                  <Pencil />
                  Rename
                </Button>
                <ArchiveButton
                  workspace={workspace}
                  disabled={workspaces.length <= 1}
                />
              </div>
            )}
          </li>
        ))}
      </ul>
      <NewWorkspace />
    </section>
  )
}
