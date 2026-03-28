import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchThreads, createThread, deleteThread, fetchHistory } from "@/lib/api/threads"
import type { ThreadCreate } from "@/lib/types"

export const THREADS_KEY = ["threads"]

export function useThreads(assistantId?: string) {
  return useQuery({
    queryKey: [...THREADS_KEY, assistantId],
    queryFn: async () => {
      const all = await fetchThreads()
      return assistantId
        ? all.filter((t) => t.assistant_id === assistantId)
        : all
    },
  })
}

export function useCreateThread() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ThreadCreate) => createThread(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: THREADS_KEY }),
  })
}

export function useDeleteThread() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteThread(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: THREADS_KEY }),
  })
}

export function useThreadHistory(threadId: string) {
  return useQuery({
    queryKey: ["history", threadId],
    queryFn: () => fetchHistory(threadId),
  })
}
