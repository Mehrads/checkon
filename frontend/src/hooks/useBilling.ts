import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"

import { type BillingOut, BillingService, type PlanIn } from "@/client"
import { isLoggedIn } from "./useAuth"

export type PlanId = PlanIn["plan"]

/** On Starter or Agency: a company profile, pay suggestions, audits and the archive. A free account has checks and
 * history only. */
export function isPaid(billing?: BillingOut | null): boolean {
  return Boolean(billing?.plan) && billing?.plan !== "free"
}

/** The API's message for a failed request, if it sent one. */
export function apiMessage(error: Error, fallback: string): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (detail?.message) return detail.message
  }
  return fallback
}

export function apiStatus(error: Error): number | undefined {
  return error instanceof AxiosError ? error.response?.status : undefined
}

/** The signed-in user's plan and this period's checks. */
export function useBilling() {
  return useQuery({
    queryKey: ["billing"],
    queryFn: async () => (await BillingService.readBilling()).data,
    enabled: isLoggedIn(),
  })
}

const CHECKS_LOADED = 100 // the most the API sends at once

/** The latest checks on the plan, for one client workspace (Agency) or all of them. */
export function usePaidChecks(workspaceId?: string) {
  return useQuery({
    queryKey: ["paidChecks", workspaceId ?? "all"],
    queryFn: async () =>
      (
        await BillingService.readPaidChecks({
          query: { workspace_id: workspaceId, limit: CHECKS_LOADED },
        })
      ).data,
    enabled: isLoggedIn(),
  })
}

/** Refresh the meter and the history after a check. */
export function useRefreshBilling() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: ["billing"] })
    queryClient.invalidateQueries({ queryKey: ["paidChecks"] })
  }
}

/** Go to Stripe Checkout for a plan. `onError` gets the plan and the error (503: Stripe isn't set up). */
export function useCheckout(onError: (plan: PlanId, error: Error) => void) {
  return useMutation({
    mutationFn: async (plan: PlanId) =>
      (await BillingService.startCheckout({ body: { plan } })).data,
    onSuccess: ({ url }) => window.location.assign(url),
    onError: (error, plan) => onError(plan, error),
  })
}

/** Go to Stripe's customer portal: card, invoices, cancelling. */
export function usePortal(onError: (error: Error) => void) {
  return useMutation({
    mutationFn: async () => (await BillingService.openBillingPortal()).data,
    onSuccess: ({ url }) => window.location.assign(url),
    onError,
  })
}
