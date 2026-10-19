import { useMutation } from "@tanstack/react-query"
import { ThumbsDown, ThumbsUp } from "lucide-react"
import { useState } from "react"

import { ChecksService, type FeedbackIn } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"

type Reason = NonNullable<FeedbackIn["reason"]>

const REASONS: { value: Reason; label: string }[] = [
  { value: "wrong_rule", label: "Wrong rule" },
  { value: "missed_issue", label: "Missed an issue" },
  { value: "bad_wording", label: "Bad wording" },
  { value: "other", label: "Something else" },
]

function useSend() {
  return useMutation({
    mutationFn: (body: FeedbackIn) => ChecksService.sendFeedback({ body }),
  })
}

interface TargetProps {
  checkId: string
  kind: "finding" | "patch"
  target: string
}

/** Thumbs up or down on one finding or patch; down asks why. */
export function FeedbackButtons({ checkId, kind, target }: TargetProps) {
  const send = useSend()
  const [down, setDown] = useState(false)
  const [comment, setComment] = useState("")
  const base = { check_id: checkId, target_kind: kind, target_id: target }

  if (send.isSuccess) {
    return <span className="text-xs text-muted-foreground">Thanks</span>
  }
  if (down) {
    return (
      <div className="flex flex-col gap-2">
        <Input
          value={comment}
          onChange={(event) => setComment(event.target.value.slice(0, 2000))}
          placeholder="What's wrong? (optional)"
          className="h-8 text-sm"
        />
        <div className="flex flex-wrap gap-1">
          {REASONS.map((reason) => (
            <Button
              key={reason.value}
              size="sm"
              variant="outline"
              disabled={send.isPending}
              onClick={() =>
                send.mutate({
                  ...base,
                  rating: "down",
                  reason: reason.value,
                  comment: comment || null,
                })
              }
            >
              {reason.label}
            </Button>
          ))}
        </div>
      </div>
    )
  }
  return (
    <div className="flex gap-1">
      <Button
        size="icon"
        variant="ghost"
        className="size-7"
        aria-label="This is right"
        disabled={send.isPending}
        onClick={() => send.mutate({ ...base, rating: "up" })}
      >
        <ThumbsUp className="size-4" />
      </Button>
      <Button
        size="icon"
        variant="ghost"
        className="size-7"
        aria-label="This is wrong"
        onClick={() => setDown(true)}
      >
        <ThumbsDown className="size-4" />
      </Button>
    </div>
  )
}

/** "This looks wrong" for the whole check; the posting is shared only with consent. */
export function LooksWrong({ checkId }: { checkId: string }) {
  const send = useSend()
  const [open, setOpen] = useState(false)
  const [comment, setComment] = useState("")
  const [share, setShare] = useState(false)

  if (send.isSuccess) {
    return (
      <p className="text-sm text-muted-foreground">
        Thanks. We review every report.
      </p>
    )
  }
  if (!open) {
    return (
      <Button
        variant="link"
        className="self-start px-0"
        onClick={() => setOpen(true)}
      >
        This looks wrong
      </Button>
    )
  }
  return (
    <div className="flex flex-col gap-2 rounded-md border p-3">
      <textarea
        value={comment}
        onChange={(event) => setComment(event.target.value.slice(0, 2000))}
        placeholder="What looks wrong?"
        className="min-h-20 w-full rounded-md border bg-transparent p-2 text-sm"
        aria-label="What looks wrong"
      />
      <div className="flex items-center gap-2 text-sm">
        <Checkbox
          id={`share-${checkId}`}
          checked={share}
          onCheckedChange={(checked) => setShare(checked === true)}
        />
        <label htmlFor={`share-${checkId}`}>
          Share this posting with us so we can fix the mistake
        </label>
      </div>
      <Button
        size="sm"
        className="self-start"
        disabled={send.isPending}
        onClick={() =>
          send.mutate({
            check_id: checkId,
            target_kind: "check",
            target_id: "check",
            rating: "looks_wrong",
            comment: comment || null,
            share_posting: share,
          })
        }
      >
        Send report
      </Button>
    </div>
  )
}
