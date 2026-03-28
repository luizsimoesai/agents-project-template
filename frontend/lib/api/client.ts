import { useAuthStore } from "@/lib/store/auth"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:2024"

let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  // Deduplicate concurrent 401s: if a refresh is already in flight, wait for it
  if (refreshPromise) return refreshPromise

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
      // Fetch current user separately to avoid using potentially null user from store
      const meRes = await fetch(`${API_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      })
      if (!meRes.ok) return false
      const user = await meRes.json()
      useAuthStore.getState().setAuth(data.access_token, user)
      localStorage.setItem("refresh_token", data.refresh_token)
      return true
    } catch {
      return false
    }
  })()

  try {
    return await refreshPromise
  } finally {
    // Clear only after all awaiters have received the result
    refreshPromise = null
  }
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
    // Refresh failed — clear auth and redirect
    useAuthStore.getState().clearAuth()
    if (typeof window !== "undefined") {
      window.location.href = "/login"
      // Return the 401 response — callers should not process it, but
      // we cannot throw here without breaking callers that use .then()
    }
    return res
  }

  return res
}
