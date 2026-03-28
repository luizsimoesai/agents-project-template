import { apiClient } from "./client"
import type { ThreadRead, ThreadCreate, MessageRead } from "@/lib/types"

export async function fetchThreads(): Promise<ThreadRead[]> {
  const res = await apiClient("/api/v1/threads")
  if (!res.ok) throw new Error("Erro ao buscar conversas")
  return res.json()
}

export async function createThread(data: ThreadCreate): Promise<ThreadRead> {
  const res = await apiClient("/api/v1/threads", {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error("Erro ao criar conversa")
  return res.json()
}

export async function deleteThread(id: string): Promise<void> {
  const res = await apiClient(`/api/v1/threads/${id}`, { method: "DELETE" })
  if (!res.ok) throw new Error("Erro ao apagar conversa")
}

export async function fetchHistory(threadId: string): Promise<MessageRead[]> {
  const res = await apiClient(`/api/v1/threads/${threadId}/history`)
  if (!res.ok) throw new Error("Erro ao buscar histórico")
  return res.json()
}
