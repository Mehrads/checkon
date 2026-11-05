import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"

import { AuditReport } from "@/components/Audit/AuditReport"
import { PageHeading } from "@/components/Common/PageHeading"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { useAudit } from "@/hooks/useAudits"
import { apiMessage } from "@/lib/api"

export const Route = createFileRoute("/_layout/audits/$auditId/")({
  component: Report,
  // Set when the user has just picked the postings: their checks start as the page opens
  validateSearch: (search: Record<string, unknown>): { run?: boolean } => ({
    run: search.run === true || search.run === "true" ? true : undefined,
  }),
  head: () => ({
    meta: [
      {
        title: "Careers page audit - CheckON",
      },
    ],
  }),
})

function Report() {
  const { auditId } = Route.useParams()
  const { run } = Route.useSearch()
  const { data: audit, error, isPending } = useAudit(auditId)
  return (
    <div className="flex flex-col gap-8">
      <div className="space-y-4">
        <Link
          to="/audits"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> All audits
        </Link>
        <PageHeading eyebrow="Careers page audit" title="Audit report" />
      </div>
      {isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : error || !audit ? (
        <Alert variant="destructive">
          <AlertDescription>
            {error
              ? apiMessage(error, "We couldn't load this audit.")
              : "Audit not found."}
          </AlertDescription>
        </Alert>
      ) : (
        <AuditReport audit={audit} run={Boolean(run)} />
      )}
    </div>
  )
}
