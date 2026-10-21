import { CalendarClock } from "lucide-react"

import type { Reminder } from "@/client"

/** What the employer still has to do once the posting is up: duties the posting text can't show. */
export function AfterPosting({ reminders }: { reminders: Reminder[] }) {
  if (reminders.length === 0) return null
  return (
    <div className="border-t bg-muted/40 px-5 py-4">
      <h3 className="flex items-center gap-2 font-semibold">
        <CalendarClock className="size-4 text-primary" aria-hidden="true" />
        After you post
      </h3>
      <p className="text-sm text-muted-foreground">
        The posting text can't show these, so they aren't part of the check.
      </p>
      <ul className="mt-3 space-y-3">
        {reminders.map((reminder) => (
          <li key={reminder.rule} className="space-y-1">
            <p className="text-sm">{reminder.text}</p>
            <p className="text-xs text-muted-foreground/80">
              {reminder.citation}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}
