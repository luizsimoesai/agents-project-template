import { apiClient } from "./client"
import type { ThreadRead, ThreadCreate, MessageRead } from "@/lib/types"

async function throwOnError(res: Response, fallback: string): Promise<never> {
  try {
    const err = await res.json()
    const detail = typeof err.detail === "string" ? err.detail : fallback
    throw new Error(detail)
  } catch {
    throw new Error(fallback)
  }
}

export async function fetchThreads(): Promise<ThreadRead[]> {
  const res = await apiClient("/api/v1/threads")
  if (!res.ok) return throwOnError(res, "Erro ao buscar conversas")
  return res.json()
}

export async function createThread(data: ThreadCreate): Promise<ThreadRead> {
  const res = await apiClient("/api/v1/threads", {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) return throwOnError(res, "Erro ao criar conversa")
  return res.json()
}

export async function deleteThread(id: string): Promise<void> {
  const res = await apiClient(`/api/v1/threads/${id}`, { method: "DELETE" })
  if (!res.ok) return throwOnError(res, "Erro ao apagar conversa")
}

export async function fetchHistory(threadId: string): Promise<MessageRead[]> {
  const res = await apiClient(`/api/v1/threads/${threadId}/history`)
  if (!res.ok) return throwOnError(res, "Erro ao buscar histórico")
  return res.json()
}
