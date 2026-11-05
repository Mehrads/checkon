import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, ExternalLink } from "lucide-react"

import { type AuditPublic, AuditsService } from "@/client"
import { Checker } from "@/components/Check/Checker"
import { PageHeading } from "@/components/Common/PageHeading"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { LoadingButton } from "@/components/ui/loading-button"
import { Skeleton } from "@/components/ui/skeleton"
import { useRefreshAccount } from "@/hooks/useAccount"
import { useAudit } from "@/hooks/useAudits"
import { useWorkspaces } from "@/hooks/useWorkspace"
import { apiMessage, apiStatus } from "@/lib/api"

export const Route = createFileRoute("/_layout/audits/$auditId/$postingId")({
  component: PostingCheck,
  head: () => ({
    meta: [
      {
        title: "Audited posting - CheckON",
      },
    ],
  }),
})

/** One audited posting's full check: findings, questions and fixes, while it's open (an hour after it ran). */
function PostingCheck() {
  const { auditId, postingId } = Route.useParams()
  const queryClient = useQueryClient()
  const refresh = useRefreshAccount()
  const { workspaces, clients } = useWorkspaces(true)
  const { data: audit } = useAudit(auditId)
  const posting = audit?.postings.find((p) => p.id === postingId)
  const profile = workspaces.find((w) => w.id === audit?.workspace_id)

  const check = useQuery({
    queryKey: ["auditCheck", auditId, postingId],
    queryFn: async () =>
      (
        await AuditsService.readPostingCheck({
          path: { audit_id: auditId, posting_id: postingId },
        })
      ).data,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY, // the Checker holds the check from here on
  })

  const again = useMutation({
    mutationFn: async () =>
      (
        await AuditsService.checkPosting({
          path: { audit_id: auditId, posting_id: postingId },
        })
      ).data,
    onSuccess: (updated) => {
      queryClient.setQueryData<AuditPublic>(["audit", auditId], (old) =>
        old
          ? {
              ...old,
              postings: old.postings.map((p) =>
                p.id === updated.id ? updated : p,
              ),
            }
          : old,
      )
      queryClient.invalidateQueries({
        queryKey: ["auditCheck", auditId, postingId],
      })
      refresh()
    },
  })

  const expired = check.error && apiStatus(check.error) === 410
  const unchecked = posting && ["refused", "failed"].includes(posting.status)

  return (
    <div className="flex flex-col gap-8">
      <div className="space-y-4">
        <Link
          to="/audits/$auditId"
          params={{ auditId }}
          search={{}}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> Audit report
        </Link>
        <PageHeading
          eyebrow="Careers page audit"
          title={posting?.title ?? "Posting"}
        >
          {posting && (
            <a
              href={posting.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 underline-offset-4 hover:underline"
            >
              {posting.location ?? "Open the posting"}
              <ExternalLink className="size-3.5" aria-hidden="true" />
            </a>
          )}
        </PageHeading>
      </div>
      {check.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : check.data ? (
        <Checker
          key={check.data.check_id}
          layout="app"
          opened={check.data}
          onChecked={refresh}
          profile={profile}
          client={clients}
        />
      ) : expired || unchecked ? (
        <Alert>
          <AlertTitle>
            {unchecked
              ? "This posting wasn't checked"
              : "This check has closed"}
          </AlertTitle>
          <AlertDescription className="space-y-3">
            <p>
              {unchecked
                ? posting?.note
                : "A check stays open for an hour after it runs, and we don't keep postings. Check it again to see its findings and fixes."}
            </p>
            {again.error && (
              <p className="text-destructive">
                {apiMessage(again.error, "We couldn't check it. Try again.")}
              </p>
            )}
            <LoadingButton
              loading={again.isPending}
              onClick={() => again.mutate()}
            >
              Check it again (uses 1 check)
            </LoadingButton>
          </AlertDescription>
        </Alert>
      ) : (
        <Alert variant="destructive">
          <AlertDescription>
            {check.error
              ? apiMessage(check.error, "We couldn't open this check.")
              : "Not found."}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
