import type { AccountOut } from "@/client"

/** "12 checks in the last 30 days", or "12 of 50 checks…" when the server limits them. */
export function usageText({ checks_used, checks_limit }: AccountOut): string {
  const total = checks_limit ?? checks_used
  const noun = total === 1 ? "check" : "checks"
  return checks_limit == null
    ? `${checks_used} ${noun} in the last 30 days`
    : `${checks_used} of ${checks_limit} ${noun} in the last 30 days`
}
