import { useQuery } from "@tanstack/react-query"

import { ReportsService } from "@/client"
import { isLoggedIn } from "./useAuth"

/** The outreach reports saved to the signed-in user's account. */
export function useMyReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: async () => (await ReportsService.readMyReports()).data,
    enabled: isLoggedIn(),
  })
}
