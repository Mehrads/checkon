import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  type WorkspacePublic,
  type WorkspacesPublic,
  WorkspacesService,
  type WorkspaceUpdate,
} from "@/client"

// Shared by the website and the browser extension, so nothing here reads the website's sign-in or router.

/** The customer's workspaces and the one checks use: its company profile. Starter has exactly one; Agency has
 * one per client (`canCreate`). `enabled`: signed in on an active plan. */
export function useWorkspaces(enabled: boolean) {
  const { data, isPending } = useQuery({
    queryKey: ["workspaces"],
    queryFn: async () => (await WorkspacesService.readWorkspaces()).data,
    enabled,
    retry: false,
  })
  return {
    workspaces: data?.data ?? [],
    current: data?.data.find((workspace) => workspace.id === data.current_id),
    canCreate: data?.can_create ?? false,
    isPending: enabled && isPending,
  }
}

function useRefresh() {
  const queryClient = useQueryClient()
  return (list?: WorkspacesPublic) => {
    if (list) queryClient.setQueryData(["workspaces"], list)
    queryClient.invalidateQueries({ queryKey: ["workspaces"] })
    queryClient.invalidateQueries({ queryKey: ["paidChecks"] })
  }
}

/** Save fields of a company profile, or rename its workspace: the whole form, or one answer from a check. */
export function useSaveProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...body }: WorkspaceUpdate & { id: string }) =>
      (
        await WorkspacesService.updateWorkspace({
          path: { workspace_id: id },
          body,
        })
      ).data,
    onSuccess: (saved: WorkspacePublic) =>
      queryClient.setQueryData<WorkspacesPublic>(["workspaces"], (list) =>
        list
          ? {
              ...list,
              data: list.data.map((w) => (w.id === saved.id ? saved : w)),
            }
          : list,
      ),
  })
}

/** Agency: pick the client workspace checks use, here and in the extension. */
export function useSwitchWorkspace() {
  const refresh = useRefresh()
  return useMutation({
    mutationFn: async (id: string) =>
      (await WorkspacesService.switchWorkspace({ body: { workspace_id: id } }))
        .data,
    onSettled: () => refresh(), // a failed switch: the workspace was archived elsewhere
  })
}

/** Agency: a workspace for a new client, which checks then use. */
export function useCreateWorkspace() {
  const refresh = useRefresh()
  return useMutation({
    mutationFn: async (name: string) =>
      (await WorkspacesService.createWorkspace({ body: { name } })).data,
    onSuccess: () => refresh(),
  })
}

/** Agency: hide a client's workspace. Its past checks keep its name. */
export function useArchiveWorkspace() {
  const refresh = useRefresh()
  return useMutation({
    mutationFn: async (id: string) =>
      (
        await WorkspacesService.archiveWorkspace({
          path: { workspace_id: id },
        })
      ).data,
    onSuccess: (list) => refresh(list),
  })
}
