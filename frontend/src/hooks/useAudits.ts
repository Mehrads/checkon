import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { useCallback, useRef, useState } from "react"

import {
  type AuditPostingPublic,
  type AuditPublic,
  AuditsService,
  type PreviewIn,
  type StartIn,
} from "@/client"
import { apiMessage } from "./useBilling"

/** Postings of one audit checked at the same time (the API allows a few). */
const AT_ONCE = 2

/** The customer's careers page audits, newest first: one client's (Agency) or all of them. */
export function useAudits(workspaceId?: string) {
  return useQuery({
    queryKey: ["audits", workspaceId ?? "all"],
    queryFn: async () =>
      (await AuditsService.readAudits({ query: { workspace_id: workspaceId } }))
        .data,
  })
}

export function useAudit(auditId: string) {
  return useQuery({
    queryKey: ["audit", auditId],
    queryFn: async () =>
      (await AuditsService.readAudit({ path: { audit_id: auditId } })).data,
    staleTime: 10_000, // just started: don't reload over the postings being checked
  })
}

/** Read the board: its open Ontario postings and the checks left. Nothing is checked yet. */
export function usePreviewAudit() {
  return useMutation({
    mutationFn: async (body: PreviewIn) =>
      (await AuditsService.previewAudit({ body })).data,
  })
}

export function useStartAudit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: StartIn) =>
      (await AuditsService.startAudit({ body })).data,
    onSuccess: (audit) => {
      queryClient.setQueryData(["audit", audit.id], audit)
      queryClient.invalidateQueries({ queryKey: ["audits"] })
    },
  })
}

function reason(error: unknown): string | undefined {
  return error instanceof AxiosError
    ? error.response?.data?.detail?.reason
    : undefined
}

/** Check postings of an audit, a few at a time, each one request (each uses a check). The report updates as each
 * one finishes; closing the page leaves the rest unchecked. */
export function useRunAudit(auditId: string, onChecked?: () => void) {
  const queryClient = useQueryClient()
  const [running, setRunning] = useState(false)
  const [stopped, setStopped] = useState<string | null>(null)
  const active = useRef(false)

  const update = useCallback(
    (posting: AuditPostingPublic) =>
      queryClient.setQueryData<AuditPublic>(["audit", auditId], (audit) =>
        audit
          ? {
              ...audit,
              postings: audit.postings.map((p) =>
                p.id === posting.id ? posting : p,
              ),
            }
          : audit,
      ),
    [auditId, queryClient],
  )

  const run = useCallback(
    async (postings: AuditPostingPublic[]) => {
      if (active.current || !postings.length) return
      active.current = true
      setRunning(true)
      setStopped(null)
      const queue = [...postings]
      const worker = async () => {
        while (queue.length && active.current) {
          const posting = queue.shift() as AuditPostingPublic
          update({ ...posting, status: "checking", note: null })
          try {
            const { data } = await AuditsService.checkPosting({
              path: { audit_id: auditId, posting_id: posting.id },
            })
            update(data)
            onChecked?.()
          } catch (error) {
            if (reason(error) === "busy") {
              queue.push(posting)
              await new Promise((resolve) => setTimeout(resolve, 3000))
            } else if (reason(error) === "plan_limit") {
              update(posting)
              active.current = false
              setStopped(
                apiMessage(error as Error, "Your plan's checks ran out."),
              )
            } else {
              update({
                ...posting,
                status: "failed",
                note: apiMessage(
                  error as Error,
                  "We couldn't check this posting. Check it again.",
                ),
              })
            }
          }
        }
      }
      await Promise.all(Array.from({ length: AT_ONCE }, worker))
      active.current = false
      setRunning(false)
      queryClient.invalidateQueries({ queryKey: ["audits"] })
    },
    [auditId, onChecked, queryClient, update],
  )

  const stop = useCallback(() => {
    active.current = false
  }, [])

  return { run, stop, running, stopped }
}
