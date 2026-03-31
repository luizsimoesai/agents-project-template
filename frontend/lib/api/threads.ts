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

// POST /threads/search — Aegra filters by owner automatically via @auth.on handler.
// Pass optional metadata filter (e.g. assistant_id) to narrow results further.
export async function fetchThreads(filter?: { assistant_id?: string }): Promise<ThreadRead[]> {
  const body = filter?.assistant_id
    ? { metadata: { assistant_id: filter.assistant_id } }
    : {}
  const res = await apiClient("/threads/search", {
    method: "POST",
    body: JSON.stringify(body),
  })
  if (!res.ok) return throwOnError(res, "Erro ao buscar conversas")
  return res.json()
}

export async function createThread(data: ThreadCreate): Promise<ThreadRead> {
  const res = await apiClient("/threads", {
    method: "POST",
    body: JSON.stringify({
      metadata: {
        assistant_id: data.assistant_id,
        ...(data.thread_name ? { thread_name: data.thread_name } : {}),
      },
    }),
  })
  if (!res.ok) return throwOnError(res, "Erro ao criar conversa")
  return res.json()
}

export async function deleteThread(id: string): Promise<void> {
  const res = await apiClient(`/threads/${id}`, { method: "DELETE" })
  if (!res.ok) return throwOnError(res, "Erro ao apagar conversa")
}
