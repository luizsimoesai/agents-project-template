import { useAuthStore } from "@/lib/store/auth"

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:2026"

let refreshPromise: Promise<boolean> | null = null

async function doRefresh(): Promise<boolean> {
  // The refresh token lives in an HttpOnly cookie the browser sends
  // automatically on credentials:"include". JS never sees it.
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
    if (!res.ok) {
      // Server rejected the refresh token — the cookie was cleared by the
      // server response if applicable, nothing for us to clean up locally.
      return false
    }
    const data = await res.json()
    const meRes = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    })
    if (!meRes.ok) {
      // /auth/me failed (deactivated user, etc.) — log out cleanly.
      useAuthStore.getState().clearAuth()
      return false
    }
    const user = await meRes.json()
    useAuthStore.getState().setAuth(data.access_token, user)
    return true
  } catch {
    return false
  }
}

export async function tryRefresh(): Promise<boolean> {
  // Single-flight: concurrent 401s share one in-flight refresh. A 401 that
  // arrives AFTER the refresh has resolved doesn't need to refresh again —
  // apiClient's "tokenAtStart vs current" check below catches that case and
  // simply retries with the rotated token. So we can null this out the
  // moment the work settles.
  if (refreshPromise) return refreshPromise

  refreshPromise = doRefresh().finally(() => {
    refreshPromise = null
  })
  return refreshPromise
}

export async function apiClient(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const tokenAtStart = useAuthStore.getState().accessToken

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }

  if (tokenAtStart) {
    headers["Authorization"] = `Bearer ${tokenAtStart}`
  }

  // credentials:"include" is required for cross-origin requests so the
  // browser sends the HttpOnly refresh cookie to /auth/refresh and /auth/logout.
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  })

  if (res.status !== 401) return res

  // If the token in the store has changed since we issued the request, a
  // concurrent refresh already rotated it — just retry with the new token
  // and skip triggering another refresh.
  const currentToken = useAuthStore.getState().accessToken
  if (currentToken && currentToken !== tokenAtStart) {
    headers["Authorization"] = `Bearer ${currentToken}`
    return fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      credentials: "include",
    })
  }

  const refreshed = await tryRefresh()
  if (refreshed) {
    const { accessToken: newToken } = useAuthStore.getState()
    if (newToken) headers["Authorization"] = `Bearer ${newToken}`
    return fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      credentials: "include",
    })
  }

  // Refresh failed — clear auth and redirect. Throw so callers don't try to
  // parse a 401 response body while navigation is in progress.
  useAuthStore.getState().clearAuth()
  if (typeof window !== "undefined") {
    window.location.href = "/login"
  }
  throw new ApiAuthError()
}

export class ApiAuthError extends Error {
  constructor() {
    super("Authentication required")
    this.name = "ApiAuthError"
  }
}
