import { Input } from "@/components/ui/input"

/** Errors from reading a link: the check didn't run, so the paste box is the way on. */
export const LINK_REFUSALS = new Set([
  "bad_url",
  "blocked_site",
  "unsafe_url",
  "fetch_failed",
  "not_a_page",
  "no_posting",
  "too_long",
  "fetch_limit",
])

export function host(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, "")
  } catch {
    return url
  }
}

/** The link to a public posting page, which the server reads. `read` is what came back from the last check by
 * link, so the user can see what was checked. */
export function PostingLink({
  value,
  onChange,
  onSubmit,
  read,
}: {
  value: string
  onChange: (value: string) => void
  onSubmit?: () => void
  read?: { url: string; characters: number } | null
}) {
  return (
    <div className="space-y-2">
      <Input
        id="posting-link"
        type="url"
        inputMode="url"
        autoComplete="url"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && value.trim()) onSubmit?.()
        }}
        placeholder="https://careers.example.com/jobs/payroll-specialist"
      />
      <p className="text-xs text-muted-foreground">
        A public page with the posting, such as your careers page or job board.
        LinkedIn, Indeed and Glassdoor can't be read: paste those postings
        instead.
      </p>
      {read && (
        <p className="text-xs text-muted-foreground">
          We read {read.characters.toLocaleString()} characters from{" "}
          {host(read.url)}. You can see and edit them under Paste text.
        </p>
      )}
    </div>
  )
}
