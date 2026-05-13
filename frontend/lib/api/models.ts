import { apiClient } from "./client"
import type { ModelCreate, ModelRead, ModelUpdate } from "@/lib/types"

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

export async function fetchModels(): Promise<ModelRead[]> {
  const res = await apiClient("/api/v1/models")
  if (!res.ok) return throwOnError(res, "Failed to fetch models")
  return res.json()
}

export async function fetchAllModels(): Promise<ModelRead[]> {
  const res = await apiClient("/api/v1/models/all")
  if (!res.ok) return throwOnError(res, "Failed to fetch all models")
  return res.json()
}

export async function createModel(data: ModelCreate): Promise<ModelRead> {
  const res = await apiClient("/api/v1/models", {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) return throwOnError(res, "Failed to create model")
  return res.json()
}

export async function updateModel(id: string, data: ModelUpdate): Promise<ModelRead> {
  const res = await apiClient(`/api/v1/models/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) return throwOnError(res, "Failed to update model")
  return res.json()
}

export async function deleteModel(id: string): Promise<void> {
  const res = await apiClient(`/api/v1/models/${id}`, { method: "DELETE" })
  if (!res.ok) return throwOnError(res, "Failed to delete model")
}
