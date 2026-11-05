import { apiClient } from "./client"
import type { UserRead, UserUpdate } from "@/lib/types"

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

export async function fetchCurrentUser(): Promise<UserRead> {
  const res = await apiClient("/api/v1/auth/me")
  if (!res.ok) return throwOnError(res, "Failed to fetch profile")
  return res.json()
}

export async function updateUser(id: string, data: UserUpdate): Promise<UserRead> {
  const res = await apiClient(`/api/v1/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) return throwOnError(res, "Failed to update profile")
  return res.json()
}

export async function fetchAllUsers(): Promise<UserRead[]> {
  const res = await apiClient("/api/v1/users")
  if (!res.ok) return throwOnError(res, "Failed to fetch users")
  return res.json()
}

export async function activateUser(id: string): Promise<UserRead> {
  const res = await apiClient(`/api/v1/users/${id}/activate`, { method: "PATCH" })
  if (!res.ok) return throwOnError(res, "Failed to activate user")
  return res.json()
}

export async function deactivateUser(id: string): Promise<UserRead> {
  const res = await apiClient(`/api/v1/users/${id}/deactivate`, { method: "PATCH" })
  if (!res.ok) return throwOnError(res, "Failed to deactivate user")
  return res.json()
}

export async function deleteUser(id: string): Promise<void> {
  const res = await apiClient(`/api/v1/users/${id}`, { method: "DELETE" })
  if (!res.ok) return throwOnError(res, "Failed to delete user")
}
