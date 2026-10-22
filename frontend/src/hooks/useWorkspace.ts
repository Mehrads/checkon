import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { type ProfileUpdate, WorkspacesService } from "@/client"

// Shared by the website and the browser extension, so nothing here reads the website's sign-in or router.

/** The company profile a customer's checks start from. `enabled`: signed in on an active plan. */
export function useWorkspace(enabled: boolean) {
  return useQuery({
    queryKey: ["workspace"],
    queryFn: async () => (await WorkspacesService.readCurrentWorkspace()).data,
    enabled,
    retry: false,
  })
}

/** Save fields of a company profile: the whole form, or one answer given during a check. */
export function useSaveProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...body }: ProfileUpdate & { id: string }) =>
      (
        await WorkspacesService.updateWorkspace({
          path: { workspace_id: id },
          body,
        })
      ).data,
    onSuccess: (data) => queryClient.setQueryData(["workspace"], data),
  })
}
