import { apiClient } from "./client"
import type { ThreadRead, ThreadCreate } from "@/lib/types"

async function throwOnError(res: Response, fallback: string): Promise<never> {
  let detail = fallback
  try {
    const err = await res.json()
    if (typeof err.detail === "string") detail = err.detail
  } catch {
    // non-JSON body, use fallback
  }
  throw new Error(detail)
}

// POST /threads/search — Aegra scopes results to the authenticated user via identity.
// We fetch all threads for the user and filter client-side, avoiding metadata filter
// format differences between thread creation paths (native vs legacy).
export async function fetchThreads(): Promise<ThreadRead[]> {
  const res = await apiClient("/threads/search", {
    method: "POST",
    body: JSON.stringify({}),
  })
  if (!res.ok) return throwOnError(res, "Erro ao buscar conversas")
  const data = await res.json()
  // Handle both plain array and wrapped { threads: [...] } response shapes
  return Array.isArray(data) ? data : (data.threads ?? [])
}

export async function createThread(data: ThreadCreate): Promise<ThreadRead> {
  const res = await apiClient("/threads", {
    method: "POST",
    body: JSON.stringify({
      metadata: {
        // assistant_id is overwritten by Aegra; use thread_assistant_id as our custom key
        thread_assistant_id: data.assistant_id,
        ...(data.thread_name ? { thread_name: data.thread_name } : {}),
      },
    }),
  })
  if (!res.ok) return throwOnError(res, "Erro ao criar conversa")
  return res.json()
}

export async function updateThreadMetadata(
  id: string,
  metadata: Record<string, unknown>
): Promise<ThreadRead> {
  const res = await apiClient(`/threads/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ metadata }),
  })
  if (!res.ok) return throwOnError(res, "Erro ao atualizar conversa")
  return res.json()
}

export async function deleteThread(id: string): Promise<void> {
  const res = await apiClient(`/threads/${id}`, { method: "DELETE" })
  if (!res.ok) return throwOnError(res, "Erro ao apagar conversa")
}

// GET /threads/{id}/state — returns the current thread state including all messages.
// Returns an empty array if the thread has no state yet (new thread).
export async function fetchThreadState(threadId: string): Promise<unknown[]> {
  const res = await apiClient(`/threads/${threadId}/state`)
  if (!res.ok) return []
  const data = await res.json()
  return data?.values?.messages ?? []
}
