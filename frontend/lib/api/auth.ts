import { apiClient } from "./client"
import { useAuthStore } from "@/lib/store/auth"
import type { TokenResponse, UserRead, UserCreate } from "@/lib/types"

export async function login(email: string, password: string): Promise<void> {
  const res = await apiClient("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(
      typeof err.detail === "string" ? err.detail : "Credenciais inválidas"
    )
  }
  const data: TokenResponse = await res.json()
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
    const err = await res.json()
    throw new Error(
      typeof err.detail === "string" ? err.detail : "Erro ao criar conta"
    )
  }
  return res.json()
}

async function getMe(token: string): Promise<UserRead> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:2024"
  const res = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("Falha ao buscar perfil")
  return res.json()
}

export async function refreshSession(): Promise<void> {
  const refreshToken = localStorage.getItem("refresh_token")
  if (!refreshToken) throw new Error("No refresh token")
  const res = await apiClient("/api/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!res.ok) throw new Error("Refresh failed")
  const data: TokenResponse = await res.json()
  localStorage.setItem("refresh_token", data.refresh_token)
  const user = await getMe(data.access_token)
  useAuthStore.getState().setAuth(data.access_token, user)
}
