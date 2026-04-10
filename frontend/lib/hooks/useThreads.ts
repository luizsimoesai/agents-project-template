import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchThreads, createThread, deleteThread, fetchThreadState, updateThreadMetadata } from "@/lib/api/threads"

import type { ThreadCreate } from "@/lib/types"

export const THREADS_KEY = ["threads"]

export function useThreads(assistantId?: string) {
  return useQuery({
    queryKey: THREADS_KEY,
    queryFn: fetchThreads,
    select: (threads) =>
      assistantId
        ? threads.filter(
            (t) =>
              t.metadata?.thread_assistant_id === assistantId ||
              t.metadata?.assistant_id === assistantId
          )
        : threads,
  })
}

export function useCreateThread() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ThreadCreate) => createThread(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: THREADS_KEY }),
  })
}

export function useUpdateThreadName() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      updateThreadMetadata(id, { thread_name: name }),
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

// Loads prior messages from an existing thread via GET /threads/{id}/state.
// Used as a fallback in ChatView until useStream starts receiving live messages.
export function useThreadState(threadId: string) {
  return useQuery({
    queryKey: ["thread-state", threadId],
    queryFn: () => fetchThreadState(threadId),
    staleTime: Infinity, // don't re-fetch — useStream takes over once active
  })
}
