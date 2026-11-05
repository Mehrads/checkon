import { Placeholder } from "@tiptap/extensions"
import { type Editor, EditorContent, useEditor } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import {
  Archive,
  Bold,
  Check,
  Copy,
  Heading2,
  Heading3,
  Italic,
  Link2,
  List,
  ListOrdered,
  type LucideIcon,
  Quote,
  Redo2,
  RotateCcw,
  Undo2,
} from "lucide-react"
import { type ReactNode, useMemo, useState } from "react"

import type { FinalOut } from "@/client"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { useSaveArchivedText } from "@/hooks/useArchive"
import { track } from "@/lib/analytics"
import { apiMessage } from "@/lib/api"
import { copyToClipboard } from "@/lib/clipboard"
import { countWords, docToPlainText, textToHtml } from "@/lib/posting-format"
import { cn } from "@/lib/utils"
import { FINAL_STATUS_TEXT } from "./labels"
import { StatusIcon } from "./StatusIcon"

interface Tool {
  label: string
  icon: LucideIcon
  active?: (editor: Editor) => boolean
  run: (editor: Editor) => void
  disabled?: (editor: Editor) => boolean
}

const TOOLS: (Tool | "divider")[] = [
  {
    label: "Title",
    icon: Heading2,
    active: (e) => e.isActive("heading", { level: 2 }),
    run: (e) => e.chain().focus().toggleHeading({ level: 2 }).run(),
  },
  {
    label: "Section heading",
    icon: Heading3,
    active: (e) => e.isActive("heading", { level: 3 }),
    run: (e) => e.chain().focus().toggleHeading({ level: 3 }).run(),
  },
  "divider",
  {
    label: "Bold",
    icon: Bold,
    active: (e) => e.isActive("bold"),
    run: (e) => e.chain().focus().toggleBold().run(),
  },
  {
    label: "Italic",
    icon: Italic,
    active: (e) => e.isActive("italic"),
    run: (e) => e.chain().focus().toggleItalic().run(),
  },
  {
    label: "Link",
    icon: Link2,
    active: (e) => e.isActive("link"),
    run: (e) => {
      if (e.isActive("link")) {
        e.chain().focus().unsetLink().run()
        return
      }
      const url = window.prompt("Link to")?.trim()
      if (url)
        e.chain().focus().extendMarkRange("link").setLink({ href: url }).run()
    },
  },
  "divider",
  {
    label: "Bulleted list",
    icon: List,
    active: (e) => e.isActive("bulletList"),
    run: (e) => e.chain().focus().toggleBulletList().run(),
  },
  {
    label: "Numbered list",
    icon: ListOrdered,
    active: (e) => e.isActive("orderedList"),
    run: (e) => e.chain().focus().toggleOrderedList().run(),
  },
  {
    label: "Quote",
    icon: Quote,
    active: (e) => e.isActive("blockquote"),
    run: (e) => e.chain().focus().toggleBlockquote().run(),
  },
  "divider",
  {
    label: "Undo",
    icon: Undo2,
    run: (e) => e.chain().focus().undo().run(),
    disabled: (e) => !e.can().undo(),
  },
  {
    label: "Redo",
    icon: Redo2,
    run: (e) => e.chain().focus().redo().run(),
    disabled: (e) => !e.can().redo(),
  },
]

/** A link to an archived posting: the website's router, or a new tab from the extension. */
export type ArchiveLink = (label: string, postingId: string) => ReactNode

/** "Saved to the archive", under the editor's header when the check's workspace keeps postings, and a button
 * to save the edits made here: the archive should hold what actually goes up. */
function ArchiveNote({
  postingId,
  editor,
  edited,
  onSaved,
  link,
}: {
  postingId: string
  editor: Editor | null
  edited: boolean
  onSaved: () => void
  link?: ArchiveLink
}) {
  const save = useSaveArchivedText(postingId)
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-primary/5 px-5 py-2.5 text-sm">
      <p className="flex items-center gap-2">
        <Archive className="size-4 shrink-0 text-primary" aria-hidden="true" />
        <span>
          {save.isSuccess && !edited
            ? "Your edits are saved to the archive."
            : "Saved to the archive."}{" "}
          {link?.("Open it", postingId)}
        </span>
      </p>
      {edited && (
        <LoadingButton
          size="sm"
          variant="outline"
          loading={save.isPending}
          disabled={!editor}
          onClick={() =>
            editor &&
            save.mutate(docToPlainText(editor.getJSON()), {
              onSuccess: onSaved,
            })
          }
        >
          Save edits to the archive
        </LoadingButton>
      )}
      {save.isError && (
        <p className="w-full text-destructive">
          {apiMessage(
            save.error,
            "We couldn't save your edits to the archive.",
          )}
        </p>
      )}
    </div>
  )
}

/** The updated posting as a document: edit and format it, then copy it into your ATS or careers page. */
export function PostingEditor({
  final,
  onInsert,
  archiveLink,
}: {
  final: FinalOut
  /** The browser extension: write the edited posting back into the page's job form. */
  onInsert?: (html: string, text: string) => Promise<boolean>
  /** Where "Saved to the archive" links to. */
  archiveLink?: ArchiveLink
}) {
  const initial = useMemo(() => textToHtml(final.text), [final.text])
  const [copied, setCopied] = useState<"rich" | "plain" | null>(null)
  const [copyFailed, setCopyFailed] = useState(false)
  const [inserted, setInserted] = useState<boolean | null>(null)
  const [edited, setEdited] = useState(false) // since the archive last saved it
  const [shown, setShown] = useState(final)
  if (shown !== final) {
    setShown(final) // applied again: the archive has this text
    setEdited(false)
  }
  const editor = useEditor(
    {
      onUpdate: () => setEdited(true),
      extensions: [
        StarterKit.configure({
          heading: { levels: [2, 3] },
          code: false,
          codeBlock: false,
          horizontalRule: false,
          link: {
            openOnClick: false,
            autolink: true,
            defaultProtocol: "https",
          },
        }),
        Placeholder.configure({ placeholder: "Your posting is empty." }),
      ],
      content: initial,
      shouldRerenderOnTransaction: true,
      editorProps: {
        attributes: {
          class: "posting-doc",
          role: "textbox",
          "aria-multiline": "true",
          "aria-label": "Updated job posting",
        },
      },
    },
    [initial],
  )

  const copy = async (rich: boolean, button: HTMLButtonElement) => {
    if (!editor) return
    const done = await copyToClipboard(docToPlainText(editor.getJSON()), {
      html: rich ? editor.getHTML() : undefined,
      focus: button,
    })
    setCopyFailed(!done)
    if (!done) return
    setCopied(rich ? "rich" : "plain")
    setTimeout(() => setCopied(null), 2000)
    track("copy", { format: rich ? "formatted" : "plain" })
  }

  const insert = async () => {
    if (!editor || !onInsert) return
    const ok = await onInsert(
      editor.getHTML(),
      docToPlainText(editor.getJSON()),
    ).catch(() => false)
    setInserted(ok)
    if (ok) setTimeout(() => setInserted(null), 2000)
  }

  return (
    <section
      aria-labelledby="updated-posting"
      className="overflow-hidden rounded-xl border bg-card shadow-sm"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
        <div className="flex items-center gap-3">
          <StatusIcon status={final.report.status} />
          <div>
            <h2 id="updated-posting" className="font-semibold">
              Your updated posting
            </h2>
            <p className="text-sm text-muted-foreground">
              {FINAL_STATUS_TEXT[final.report.status]}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {onInsert && (
            <Button onClick={insert} disabled={!editor}>
              {inserted ? <Check /> : null}
              {inserted ? "Inserted" : "Insert into page"}
            </Button>
          )}
          <Button
            variant={onInsert ? "outline" : "default"}
            onClick={(event) => copy(true, event.currentTarget)}
            disabled={!editor}
          >
            {copied === "rich" ? <Check /> : <Copy />}
            {copied === "rich" ? "Copied" : "Copy formatted"}
          </Button>
          <Button
            variant="outline"
            onClick={(event) => copy(false, event.currentTarget)}
            disabled={!editor}
          >
            {copied === "plain" ? "Copied" : "Copy plain text"}
          </Button>
        </div>
        {copyFailed && (
          <p className="w-full text-sm text-destructive">
            We couldn't copy here. Select the posting below and copy it.
          </p>
        )}
        {inserted === false && (
          <p className="w-full text-sm text-destructive">
            We couldn't write into that field. Use Copy formatted and paste it
            instead.
          </p>
        )}
      </header>

      {final.archived && (
        <ArchiveNote
          key={final.archived.id}
          postingId={final.archived.id}
          editor={editor}
          edited={edited}
          onSaved={() => setEdited(false)}
          link={archiveLink}
        />
      )}

      <div
        role="toolbar"
        aria-label="Formatting"
        className="flex flex-wrap items-center gap-0.5 border-b bg-muted/40 px-3 py-1.5"
      >
        {TOOLS.map((tool, index) =>
          tool === "divider" ? (
            <span
              key={`divider-${index}`}
              className="mx-1 h-5 w-px bg-border"
              aria-hidden="true"
            />
          ) : (
            <button
              key={tool.label}
              type="button"
              title={tool.label}
              aria-label={tool.label}
              aria-pressed={
                editor && tool.active ? tool.active(editor) : undefined
              }
              disabled={!editor || (tool.disabled?.(editor) ?? false)}
              // Keep the editor's selection: run on click, but don't take focus on mousedown.
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => editor && tool.run(editor)}
              className={cn(
                "inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-40",
                editor && tool.active?.(editor) && "bg-accent text-foreground",
              )}
            >
              <tool.icon className="size-4" />
            </button>
          ),
        )}
        <button
          type="button"
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => editor?.commands.setContent(initial)}
          className="ml-auto inline-flex h-8 items-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <RotateCcw className="size-3.5" /> Start over
        </button>
      </div>

      <div className="px-6 py-5 sm:px-10 sm:py-8">
        <EditorContent editor={editor} />
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t px-5 py-3 text-xs text-muted-foreground">
        <span>
          {editor ? countWords(editor.getText()).toLocaleString() : 0} words
        </span>
        <span>
          Your edits here aren't re-checked. Keep the pay, vacancy and AI
          statements when you edit.
        </span>
      </footer>
    </section>
  )
}
