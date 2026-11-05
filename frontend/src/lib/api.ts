import { AxiosError } from "axios"

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

/** The API's reason for refusing a request ("signup_closed", "account_limit", …), if it gave one. */
export function apiReason(error: unknown): string | undefined {
  return error instanceof AxiosError
    ? error.response?.data?.detail?.reason
    : undefined
}
