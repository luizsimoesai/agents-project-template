import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  fetchAssistants,
  createAssistant,
  updateAssistant,
  deleteAssistant,
} from "@/lib/api/assistants"
import type { AssistantCreate, AssistantUpdate } from "@/lib/types"

export const ASSISTANTS_KEY = ["assistants"]

export function useAssistants() {
  return useQuery({ queryKey: ASSISTANTS_KEY, queryFn: fetchAssistants })
}

export function useCreateAssistant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AssistantCreate) => createAssistant(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSISTANTS_KEY }),
  })
}

export function useUpdateAssistant(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AssistantUpdate) => updateAssistant(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSISTANTS_KEY }),
  })
}

export function useDeleteAssistant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteAssistant(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ASSISTANTS_KEY }),
  })
}
