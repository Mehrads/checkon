import { useQuery, useQueryClient } from "@tanstack/react-query"

import { AccountService } from "@/client"
import { isLoggedIn } from "./useAuth"

/** The signed-in account's checks in the last 30 days, and the server's limit on them, if it sets one. */
export function useAccount() {
  return useQuery({
    queryKey: ["account"],
    queryFn: async () => (await AccountService.readAccount()).data,
    enabled: isLoggedIn(),
  })
}

const CHECKS_LOADED = 100 // the most the API sends at once

/** The account's latest checks, for one workspace or all of them. */
export function useAccountChecks(workspaceId?: string) {
  return useQuery({
    queryKey: ["accountChecks", workspaceId ?? "all"],
    queryFn: async () =>
      (
        await AccountService.readAccountChecks({
          query: { workspace_id: workspaceId, limit: CHECKS_LOADED },
        })
      ).data,
    enabled: isLoggedIn(),
  })
}

/** Refresh the usage and the history after a check. */
export function useRefreshAccount() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: ["account"] })
    queryClient.invalidateQueries({ queryKey: ["accountChecks"] })
  }
}
