import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createModel,
  deleteModel,
  fetchAllModels,
  fetchModels,
  updateModel,
} from "@/lib/api/models"
import type { ModelCreate, ModelUpdate } from "@/lib/types"

export const MODELS_KEY = ["models"]

export function useModels() {
  return useQuery({
    queryKey: MODELS_KEY,
    queryFn: fetchModels,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAllModels() {
  return useQuery({
    queryKey: [...MODELS_KEY, "all"],
    queryFn: fetchAllModels,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ModelCreate) => createModel(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODELS_KEY })
    },
  })
}

export function useUpdateModel(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ModelUpdate) => updateModel(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODELS_KEY })
    },
  })
}

export function useSetModelDefault() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => updateModel(id, { is_default: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODELS_KEY })
    },
  })
}

export function useDeleteModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteModel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODELS_KEY })
    },
  })
}
