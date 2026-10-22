import type { Report } from "@/client"
import { LooksWrong } from "./Feedback"
import { STATUS_TEXT } from "./labels"
import { StatusIcon } from "./StatusIcon"

/** The verdict at a glance: overall status and how many rules need attention. */
export function Summary({
  checkId,
  report,
}: {
  checkId: string
  report: Report
}) {
  const results = [...report.results, ...(report.form_results ?? [])]
  const count = (verdict: string) =>
    results.filter((r) => r.verdict === verdict).length
  const parts = [
    [count("fail"), "to fix"],
    [count("warning"), "worth fixing"],
    [count("needs_input"), "to answer"],
    [count("pass"), "passed"],
  ].filter(([n]) => Number(n) > 0)

  return (
    <section className="flex flex-col gap-3 rounded-xl border bg-card p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <StatusIcon status={report.status} />
        <div>
          <h2 className="text-lg font-semibold">
            {STATUS_TEXT[report.status]}
          </h2>
          <p className="text-sm text-muted-foreground">
            {report.message ??
              parts.map(([n, label]) => `${n} ${label}`).join(" · ")}
          </p>
        </div>
      </div>
      <LooksWrong key={checkId} checkId={checkId} />
    </section>
  )
}
