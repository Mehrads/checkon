import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  type ArchivedPostingPublic,
  type ArchivedPostingUpdate,
  ArchiveService,
} from "@/client"

// Shared by the website and the browser extension, so nothing here reads the website's sign-in or router.

export interface ArchiveQuery {
  workspaceId?: string
  q?: string
  savedFrom?: string // yyyy-mm-dd, the day saved (Toronto)
  savedTo?: string
}

/** The account's archived postings, newest first, for one workspace or all, searched by title and date. */
export function useArchive(query: ArchiveQuery, enabled = true) {
  return useQuery({
    queryKey: ["archive", query],
    queryFn: async () =>
      (
        await ArchiveService.readArchive({
          query: {
            workspace_id: query.workspaceId,
            q: query.q || undefined,
            saved_from: query.savedFrom || undefined,
            saved_to: query.savedTo || undefined,
            limit: 100,
          },
        })
      ).data,
    enabled,
    retry: false,
  })
}

export function useArchivedPosting(id: string | undefined) {
  return useQuery({
    queryKey: ["archivedPosting", id],
    queryFn: async () =>
      (await ArchiveService.readArchivedPosting({ path: { posting_id: id! } }))
        .data,
    enabled: Boolean(id),
    retry: false,
  })
}

/** After a change: the posting's own query gets the saved copy, and the list reloads. */
function useStore() {
  const queryClient = useQueryClient()
  return (posting?: ArchivedPostingPublic) => {
    if (posting)
      queryClient.setQueryData(["archivedPosting", posting.id], posting)
    queryClient.invalidateQueries({ queryKey: ["archive"] })
  }
}

/** Mark a posting taken down (or still up), or save its application form's text. */
export function useUpdateArchived(id: string) {
  const store = useStore()
  return useMutation({
    mutationFn: async (body: ArchivedPostingUpdate) =>
      (
        await ArchiveService.updateArchivedPosting({
          path: { posting_id: id },
          body,
        })
      ).data,
    onSuccess: store,
  })
}

/** Replace the archived text with the posting as edited after applying the fixes. */
export function useSaveArchivedText(id: string) {
  const store = useStore()
  return useMutation({
    mutationFn: async (text: string) =>
      (
        await ArchiveService.saveArchivedText({
          path: { posting_id: id },
          body: { text },
        })
      ).data,
    onSuccess: store,
  })
}

export function useDeleteArchived() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      ArchiveService.deleteArchivedPosting({ path: { posting_id: id } }),
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: ["archivedPosting", id] })
      queryClient.invalidateQueries({ queryKey: ["archive"] })
    },
  })
}

function useRefreshPosting(id: string) {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: ["archivedPosting", id] })
    queryClient.invalidateQueries({ queryKey: ["archive"] })
  }
}

export function useUploadArchivedFile(id: string) {
  const refresh = useRefreshPosting(id)
  return useMutation({
    mutationFn: (file: File) =>
      ArchiveService.uploadArchivedFile({
        path: { posting_id: id },
        body: { file },
      }),
    onSuccess: refresh,
  })
}

export function useDeleteArchivedFile(id: string) {
  const refresh = useRefreshPosting(id)
  return useMutation({
    mutationFn: (fileId: string) =>
      ArchiveService.deleteArchivedFile({
        path: { posting_id: id, file_id: fileId },
      }),
    onSuccess: refresh,
  })
}

function save(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** The file name the server gave the download, else `fallback`. */
function fileName(disposition: unknown, fallback: string): string {
  const match =
    typeof disposition === "string" &&
    /filename\*=UTF-8''([^;]+)/.exec(disposition)
  return match ? decodeURIComponent(match[1]) : fallback
}

export async function downloadArchivedFile(
  postingId: string,
  file: { id: string; name: string },
) {
  const response = await ArchiveService.downloadArchivedFile({
    path: { posting_id: postingId, file_id: file.id },
    responseType: "blob",
  })
  save(response.data as Blob, file.name)
}

/** A workspace's archive as one zip: an index page and a folder per posting. */
export async function exportArchive(workspaceId: string) {
  const response = await ArchiveService.exportArchive({
    query: { workspace_id: workspaceId },
    responseType: "blob",
  })
  save(
    response.data as Blob,
    fileName(response.headers["content-disposition"], "CheckON archive.zip"),
  )
}
