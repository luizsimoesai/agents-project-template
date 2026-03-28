import { apiClient } from "./client"
import type { AssistantRead, AssistantCreate, AssistantUpdate } from "@/lib/types"

export async function fetchAssistants(): Promise<AssistantRead[]> {
  const res = await apiClient("/api/v1/assistants")
  if (!res.ok) throw new Error("Erro ao buscar assistentes")
  return res.json()
}

export async function fetchAssistant(id: string): Promise<AssistantRead> {
  const res = await apiClient(`/api/v1/assistants/${id}`)
  if (!res.ok) throw new Error("Assistente não encontrado")
  return res.json()
}

export async function createAssistant(data: AssistantCreate): Promise<AssistantRead> {
  const res = await apiClient("/api/v1/assistants", {
    method: "POST",
    body: JSON.stringify({ graph_id: "agent", ...data }),
  })
  if (!res.ok) throw new Error("Erro ao criar assistente")
  return res.json()
}

export async function updateAssistant(
  id: string,
  data: AssistantUpdate
): Promise<AssistantRead> {
  const res = await apiClient(`/api/v1/assistants/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error("Erro ao atualizar assistente")
  return res.json()
}

export async function deleteAssistant(id: string): Promise<void> {
  const res = await apiClient(`/api/v1/assistants/${id}`, { method: "DELETE" })
  if (!res.ok) throw new Error("Erro ao apagar assistente")
}
