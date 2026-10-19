import { useState } from "react"

import type { Answers, Question } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

interface QuestionsProps {
  questions: Question[]
  pending: boolean
  onAnswer: (answers: Answers) => void
}

function HoursAnswer({
  pending,
  onAnswer,
}: Pick<QuestionsProps, "pending" | "onAnswer">) {
  const [hours, setHours] = useState("")
  const value = Number(hours)
  return (
    <form
      className="flex gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        onAnswer({ hours_per_week: value })
      }}
    >
      <Input
        type="number"
        min={1}
        max={80}
        step={0.5}
        value={hours}
        onChange={(event) => setHours(event.target.value)}
        className="w-28"
        aria-label="Hours a week"
      />
      <Button
        type="submit"
        variant="outline"
        disabled={pending || !(value > 0 && value <= 80)}
      >
        Save
      </Button>
    </form>
  )
}

export function Questions({ questions, pending, onAnswer }: QuestionsProps) {
  if (questions.length === 0) return null
  return (
    <Card className="border-sky-500/50">
      <CardHeader>
        <CardTitle>A few questions</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {questions.map((question) => (
          <div key={question.id} className="flex flex-col gap-2">
            <p className="text-sm">{question.text}</p>
            {question.kind === "number" && (
              <HoursAnswer pending={pending} onAnswer={onAnswer} />
            )}
            {question.kind === "choice" && (
              <div className="flex flex-wrap gap-2">
                {(question.options ?? []).map((option, index) => (
                  <Button
                    key={option}
                    variant="outline"
                    disabled={pending}
                    onClick={() =>
                      onAnswer({ [question.id]: index } as Answers)
                    }
                  >
                    {option}
                  </Button>
                ))}
              </div>
            )}
            {(question.kind ?? "yes_no") === "yes_no" && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  disabled={pending}
                  onClick={() => onAnswer({ [question.id]: true } as Answers)}
                >
                  Yes
                </Button>
                <Button
                  variant="outline"
                  disabled={pending}
                  onClick={() => onAnswer({ [question.id]: false } as Answers)}
                >
                  No
                </Button>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
