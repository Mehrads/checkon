import { useMutation } from "@tanstack/react-query"

import { ChecksService, type ResearchQuestion } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

/** One short, optional question after each result (Research guide). */
export function ResearchQuestionCard({
  checkId,
  question,
}: {
  checkId: string
  question: ResearchQuestion
}) {
  const send = useMutation({
    mutationFn: (answer: string) =>
      ChecksService.answerResearch({
        body: { check_id: checkId, question_id: question.id, answer },
      }),
  })
  return (
    <Card>
      <CardHeader>
        <CardTitle>One quick question</CardTitle>
        <CardDescription>
          Optional. It helps us decide what to build.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm">{question.text}</p>
        {send.isSuccess ? (
          <p className="text-sm text-muted-foreground">Thanks!</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {question.options.map((option) => (
              <Button
                key={option}
                size="sm"
                variant="outline"
                disabled={send.isPending}
                onClick={() => send.mutate(option)}
              >
                {option}
              </Button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
