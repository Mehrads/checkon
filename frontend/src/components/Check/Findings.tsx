import type { Report } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { FeedbackButtons } from "./Feedback"
import { ruleName, VERDICT_CLASS, VERDICT_TEXT } from "./labels"

interface FindingsProps {
  checkId: string
  report: Report
  text: string // the normalised posting the evidence spans point into
}

export function Findings({ checkId, report, text }: FindingsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Rule by rule</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="divide-y">
          {report.results.map((result) => (
            <li key={result.rule} className="flex flex-col gap-2 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">{ruleName(result.rule)}</span>
                <Badge
                  variant="outline"
                  className={VERDICT_CLASS[result.verdict]}
                >
                  {VERDICT_TEXT[result.verdict]}
                </Badge>
              </div>
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-muted-foreground">
                  {result.message}
                </p>
                <FeedbackButtons
                  checkId={checkId}
                  kind="finding"
                  target={result.rule}
                />
              </div>
              {result.verdict !== "pass" &&
                (result.evidence ?? []).map(([start, end]) => (
                  <blockquote
                    key={`${start}-${end}`}
                    className={cn(
                      "border-l-2 pl-3 text-sm",
                      result.verdict === "fail"
                        ? "border-destructive"
                        : "border-amber-500",
                    )}
                  >
                    {text.slice(start, end)}
                  </blockquote>
                ))}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
