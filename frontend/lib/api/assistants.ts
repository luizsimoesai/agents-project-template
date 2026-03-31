import { apiClient } from "./client"
import type { AssistantRead, AssistantCreate, AssistantUpdate } from "@/lib/types"

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

export async function fetchAssistants(): Promise<AssistantRead[]> {
  const res = await apiClient("/assistants")
  if (!res.ok) return throwOnError(res, "Erro ao buscar assistentes")
  const data = await res.json()
  return Array.isArray(data) ? data : (data.assistants ?? [])
}

export async function fetchAssistant(id: string): Promise<AssistantRead> {
  const res = await apiClient(`/assistants/${id}`)
  if (!res.ok) return throwOnError(res, "Assistente não encontrado")
  return res.json()
}

export async function createAssistant(data: AssistantCreate): Promise<AssistantRead> {
  const res = await apiClient("/assistants", {
    method: "POST",
    body: JSON.stringify({ graph_id: "agent", ...data }),
  })
  if (!res.ok) return throwOnError(res, "Erro ao criar assistente")
  return res.json()
}

export async function updateAssistant(
  id: string,
  data: AssistantUpdate
): Promise<AssistantRead> {
  const res = await apiClient(`/assistants/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) return throwOnError(res, "Erro ao atualizar assistente")
  return res.json()
}

export async function deleteAssistant(id: string): Promise<void> {
  const res = await apiClient(`/assistants/${id}`, { method: "DELETE" })
  if (!res.ok) return throwOnError(res, "Erro ao apagar assistente")
}
