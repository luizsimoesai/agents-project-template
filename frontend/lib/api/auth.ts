import { apiClient, tryRefresh } from "./client"
import { useAuthStore } from "@/lib/store/auth"
import type { UserRead, UserCreate } from "@/lib/types"

export async function login(email: string, password: string): Promise<void> {
  const res = await apiClient("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    let detail = "Credenciais inválidas"
    try {
      const err = await res.json()
      if (typeof err.detail === "string") detail = err.detail
    } catch { /* non-JSON body, use fallback */ }
    throw new Error(detail)
  }
  const data = await res.json()
  localStorage.setItem("refresh_token", data.refresh_token)
  const user = await getMe(data.access_token)
  useAuthStore.getState().setAuth(data.access_token, user)
}

export async function apiRegister(data: UserCreate): Promise<UserRead> {
  const res = await apiClient("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    let detail = "Erro ao criar conta"
    try {
      const err = await res.json()
      if (typeof err.detail === "string") detail = err.detail
    } catch { /* non-JSON body, use fallback */ }
    throw new Error(detail)
  }
  return res.json()
}

async function getMe(token: string): Promise<UserRead> {
  const res = await apiClient("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("Falha ao buscar perfil")
  return res.json()
}

export async function refreshSession(): Promise<void> {
  const refreshed = await tryRefresh()
  if (!refreshed) throw new Error("Refresh failed")
}
