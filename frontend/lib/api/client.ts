import { useAuthStore } from "@/lib/store/auth"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:2024"

let isRefreshing = false
let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  if (isRefreshing) return refreshPromise!
  isRefreshing = true
  refreshPromise = (async () => {
    const refreshToken = localStorage.getItem("refresh_token")
    if (!refreshToken) return false
    try {
      const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!res.ok) return false
      const data = await res.json()
      const { user } = useAuthStore.getState()
      useAuthStore.getState().setAuth(data.access_token, user!)
      localStorage.setItem("refresh_token", data.refresh_token)
      return true
    } catch {
      return false
    } finally {
      isRefreshing = false
      refreshPromise = null
    }
  })()
  return refreshPromise
}

export async function apiClient(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const { accessToken } = useAuthStore.getState()

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (res.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      const { accessToken: newToken } = useAuthStore.getState()
      if (newToken) headers["Authorization"] = `Bearer ${newToken}`
      return fetch(`${API_URL}${path}`, { ...options, headers })
    }
    useAuthStore.getState().clearAuth()
    if (typeof window !== "undefined") {
      window.location.href = "/login"
    }
  }

  return res
}
