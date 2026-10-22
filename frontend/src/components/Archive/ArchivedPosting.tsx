import { Download, FileText, Trash2, Upload } from "lucide-react"
import { useRef, useState } from "react"

import type { ArchivedPostingPublic, Status } from "@/client"
import { StatusLabel } from "@/components/Check/StatusIcon"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import {
  downloadArchivedFile,
  useArchivedPosting,
  useDeleteArchived,
  useDeleteArchivedFile,
  useUpdateArchived,
  useUploadArchivedFile,
} from "@/hooks/useArchive"
import { apiMessage } from "@/hooks/useBilling"
import useCustomToast from "@/hooks/useCustomToast"
import { formatDay } from "../Billing/UsageMeter"

export const MAX_DOCUMENTS = 5
const ACCEPT = ".pdf,.docx,.png,.jpg,.jpeg"

/** A day the API sends as yyyy-mm-dd, read in local time (Date would read it as UTC midnight). */
export function formatDate(value: string): string {
  return formatDay(`${value}T12:00:00`)
}

/** A moment's local day as yyyy-mm-dd, for a date field. */
export function localDay(moment: Date = new Date()): string {
  return new Date(moment.getTime() - moment.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 10)
}

function size(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** One archived posting in a side panel: its dates, text, application form and documents. */
export function ArchivedPostingSheet({
  id,
  onClose,
}: {
  id: string | undefined
  onClose: () => void
}) {
  const { data: posting, isError } = useArchivedPosting(id)
  return (
    <Sheet open={Boolean(id)} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-2xl">
        {posting && posting.id === id ? (
          <Details key={posting.id} posting={posting} onDeleted={onClose} />
        ) : (
          <SheetHeader>
            <SheetTitle>
              {isError ? "Posting not found" : "Loading the posting…"}
            </SheetTitle>
            <SheetDescription>
              {isError
                ? "It may have been deleted, or its 3 years are up."
                : "One moment."}
            </SheetDescription>
            {!isError && <Skeleton className="mt-4 h-64 w-full" />}
          </SheetHeader>
        )}
      </SheetContent>
    </Sheet>
  )
}

function Details({
  posting,
  onDeleted,
}: {
  posting: ArchivedPostingPublic
  onDeleted: () => void
}) {
  return (
    <>
      <SheetHeader className="border-b pr-12">
        <SheetTitle className="font-display text-2xl font-medium">
          {posting.title ?? "Untitled posting"}
        </SheetTitle>
        <SheetDescription>
          {posting.workspace_name} · Saved {formatDay(posting.created_at)}
          {posting.updated_at && ` · Edited ${formatDay(posting.updated_at)}`}
        </SheetDescription>
        {posting.final_status && (
          <p className="text-sm">
            <StatusLabel status={posting.final_status as Status} />
          </p>
        )}
      </SheetHeader>
      <div className="space-y-6 p-4">
        <TakenDown posting={posting} />
        <section className="space-y-2">
          <h3 className="text-sm font-semibold">Posting</h3>
          <div className="max-h-[28rem] overflow-y-auto rounded-lg border bg-card p-4 text-sm leading-relaxed whitespace-pre-wrap">
            {posting.text}
          </div>
        </section>
        <ApplicationForm posting={posting} />
        <Documents posting={posting} />
        <DeletePosting posting={posting} onDeleted={onDeleted} />
      </div>
    </>
  )
}

function TakenDown({ posting }: { posting: ArchivedPostingPublic }) {
  const { showErrorToast } = useCustomToast()
  const update = useUpdateArchived(posting.id)
  const [day, setDay] = useState(posting.taken_down_on ?? localDay())
  const [editing, setEditing] = useState(false)
  const save = (taken_down_on: string | null) =>
    update.mutate(
      { taken_down_on },
      {
        onSuccess: () => setEditing(false),
        onError: (error) =>
          showErrorToast(apiMessage(error, "We couldn't save that date.")),
      },
    )

  return (
    <section className="space-y-2 rounded-lg border bg-muted/40 p-4">
      <h3 className="text-sm font-semibold">Taken down</h3>
      {posting.taken_down_on && posting.kept_until && !editing ? (
        <>
          <p className="text-sm text-muted-foreground">
            Taken down {formatDate(posting.taken_down_on)}. Kept until{" "}
            {formatDate(posting.kept_until)}, then deleted.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setEditing(true)}
            >
              Change the date
            </Button>
            <LoadingButton
              size="sm"
              variant="ghost"
              loading={update.isPending}
              onClick={() => save(null)}
            >
              It's still up
            </LoadingButton>
          </div>
        </>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            {posting.taken_down_on
              ? "Pick the day the public could no longer see it."
              : "Still up. We keep it until 3 years after the day you mark it taken down."}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              type="date"
              aria-label="Day it was taken down"
              value={day}
              min={localDay(new Date(posting.created_at))}
              onChange={(event) => setDay(event.target.value)}
              className="w-44"
            />
            <LoadingButton
              size="sm"
              loading={update.isPending}
              disabled={!day}
              onClick={() => save(day)}
            >
              Mark taken down
            </LoadingButton>
            {editing && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditing(false)}
              >
                Cancel
              </Button>
            )}
          </div>
        </>
      )}
    </section>
  )
}

function ApplicationForm({ posting }: { posting: ArchivedPostingPublic }) {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const update = useUpdateArchived(posting.id)
  const [form, setForm] = useState(posting.application_form ?? "")
  const changed = form.trim() !== (posting.application_form ?? "")
  if (posting.read_only && !posting.application_form) return null

  return (
    <section className="space-y-2">
      <div>
        <h3 className="text-sm font-semibold">Application form</h3>
        <p className="text-sm text-muted-foreground">
          Paste the questions applicants answer, so the form is kept with the
          posting.
        </p>
      </div>
      <textarea
        aria-label="Application form"
        value={form}
        readOnly={posting.read_only}
        onChange={(event) => setForm(event.target.value.slice(0, 20_000))}
        placeholder="Name, email, resume, screening questions…"
        className="min-h-28 w-full resize-y rounded-lg border bg-background p-3 text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
      />
      {!posting.read_only && (
        <LoadingButton
          size="sm"
          variant="outline"
          loading={update.isPending}
          disabled={!changed}
          onClick={() =>
            update.mutate(
              { application_form: form },
              {
                onSuccess: () => showSuccessToast("Application form saved."),
                onError: (error) =>
                  showErrorToast(
                    apiMessage(error, "We couldn't save the application form."),
                  ),
              },
            )
          }
        >
          Save the form
        </LoadingButton>
      )}
    </section>
  )
}

function Documents({ posting }: { posting: ArchivedPostingPublic }) {
  const { showErrorToast } = useCustomToast()
  const upload = useUploadArchivedFile(posting.id)
  const remove = useDeleteArchivedFile(posting.id)
  const picker = useRef<HTMLInputElement>(null)
  const full = posting.documents.length >= MAX_DOCUMENTS
  if (posting.read_only && posting.documents.length === 0) return null

  const download = (file: { id: string; name: string }) =>
    downloadArchivedFile(posting.id, file).catch((error) =>
      showErrorToast(apiMessage(error, "We couldn't download that document.")),
    )

  return (
    <section className="space-y-2">
      <div>
        <h3 className="text-sm font-semibold">Linked documents</h3>
        <p className="text-sm text-muted-foreground">
          Documents the posting links to, such as a full job description or a
          benefits sheet. PDF, Word, PNG or JPG, up to 10 MB each, 5 per
          posting.
        </p>
      </div>
      {posting.documents.length > 0 && (
        <ul className="divide-y rounded-lg border">
          {posting.documents.map((file) => (
            <li key={file.id} className="flex items-center gap-3 px-3 py-2">
              <FileText
                className="size-4 shrink-0 text-muted-foreground"
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate text-sm">
                {file.name}
                <span className="ml-2 text-xs text-muted-foreground">
                  {size(file.size)}
                </span>
              </span>
              <Button
                size="icon"
                variant="ghost"
                aria-label={`Download ${file.name}`}
                onClick={() => download(file)}
              >
                <Download />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                aria-label={`Delete ${file.name}`}
                disabled={remove.isPending}
                onClick={() =>
                  remove.mutate(file.id, {
                    onError: (error) =>
                      showErrorToast(
                        apiMessage(error, "We couldn't delete that document."),
                      ),
                  })
                }
              >
                <Trash2 />
              </Button>
            </li>
          ))}
        </ul>
      )}
      {!posting.read_only && (
        <>
          <input
            ref={picker}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              event.target.value = ""
              if (file)
                upload.mutate(file, {
                  onError: (error) =>
                    showErrorToast(
                      apiMessage(error, "We couldn't upload that document."),
                    ),
                })
            }}
          />
          <LoadingButton
            size="sm"
            variant="outline"
            loading={upload.isPending}
            disabled={full}
            onClick={() => picker.current?.click()}
          >
            <Upload /> {full ? "5 documents added" : "Add a document"}
          </LoadingButton>
        </>
      )}
    </section>
  )
}

function DeletePosting({
  posting,
  onDeleted,
}: {
  posting: ArchivedPostingPublic
  onDeleted: () => void
}) {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const remove = useDeleteArchived()
  return (
    <section className="border-t pt-4">
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="ghost" className="text-destructive">
            <Trash2 /> Delete from the archive
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this posting?</DialogTitle>
            <DialogDescription>
              The posting, its application form and its documents are deleted
              now and can't be brought back. Keep your own copy if you still
              need the record.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" disabled={remove.isPending}>
                Cancel
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              loading={remove.isPending}
              onClick={() =>
                remove.mutate(posting.id, {
                  onSuccess: () => {
                    showSuccessToast("Deleted from the archive.")
                    onDeleted()
                  },
                  onError: (error) =>
                    showErrorToast(
                      apiMessage(error, "We couldn't delete the posting."),
                    ),
                })
              }
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
