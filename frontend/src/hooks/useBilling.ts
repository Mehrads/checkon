import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"

import { BillingService, type PlanIn } from "@/client"
import { isLoggedIn } from "./useAuth"

export type PlanId = PlanIn["plan"]

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

export function usePaidChecks() {
  return useQuery({
    queryKey: ["paidChecks"],
    queryFn: async () => (await BillingService.readPaidChecks()).data,
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
