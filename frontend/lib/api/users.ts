import { apiClient } from "./client"
import type { UserRead, UserUpdate } from "@/lib/types"

export async function fetchCurrentUser(): Promise<UserRead> {
  const res = await apiClient("/api/v1/auth/me")
  if (!res.ok) throw new Error("Erro ao buscar perfil")
  return res.json()
}

export async function updateUser(id: string, data: UserUpdate): Promise<UserRead> {
  const res = await apiClient(`/api/v1/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error("Erro ao atualizar perfil")
  return res.json()
}

export async function fetchAllUsers(): Promise<UserRead[]> {
  const res = await apiClient("/api/v1/users")
  if (!res.ok) throw new Error("Erro ao buscar usuários")
  return res.json()
}

export async function activateUser(id: string): Promise<UserRead> {
  const res = await apiClient(`/api/v1/users/${id}/activate`, { method: "PATCH" })
  if (!res.ok) throw new Error("Erro ao ativar usuário")
  return res.json()
}

export async function deactivateUser(id: string): Promise<UserRead> {
  const res = await apiClient(`/api/v1/users/${id}/deactivate`, { method: "PATCH" })
  if (!res.ok) throw new Error("Erro ao desativar usuário")
  return res.json()
}

export async function deleteUser(id: string): Promise<void> {
  const res = await apiClient(`/api/v1/users/${id}`, { method: "DELETE" })
  if (!res.ok) throw new Error("Erro ao apagar usuário")
}
