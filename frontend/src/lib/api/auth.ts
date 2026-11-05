import { apiClient, tryRefresh, API_URL } from "./client"
import { useAuthStore } from "@/lib/store/auth"
import type { UserRead, UserCreate } from "@/lib/types"

export async function login(email: string, password: string): Promise<void> {
  const res = await apiClient("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    let detail = "Invalid credentials"
    try {
      const err = await res.json()
      if (typeof err.detail === "string") detail = err.detail
    } catch { /* non-JSON body, use fallback */ }
    throw new Error(detail)
  }
  // The refresh token is now an HttpOnly cookie set by the server response;
  // we only see access_token in the body.
  const data = await res.json()
  const user = await getMe(data.access_token)
  useAuthStore.getState().setAuth(data.access_token, user)
}

export async function logout(): Promise<void> {
  // Best-effort: clear the cookie + invalidate server-side jti. Always wipe
  // local state, even if the network call fails.
  try {
    await fetch(`${API_URL}/api/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
    })
  } catch {
    // ignore — we still need to clear local state
  }
  useAuthStore.getState().clearAuth()
}

export async function apiRegister(data: UserCreate): Promise<UserRead> {
  const res = await apiClient("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    let detail = "Failed to create account"
    try {
      const err = await res.json()
      if (typeof err.detail === "string") detail = err.detail
    } catch { /* non-JSON body, use fallback */ }
    throw new Error(detail)
  }
  return res.json()
}

async function getMe(token: string): Promise<UserRead> {
  const res = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error("Failed to fetch profile")
  return res.json()
}

export async function refreshSession(): Promise<void> {
  const refreshed = await tryRefresh()
  if (!refreshed) throw new Error("Refresh failed")
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const res = await apiClient("/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
  if (!res.ok) {
    let detail = "Failed to change password"
    try {
      const err = await res.json()
      if (typeof err.detail === "string") detail = err.detail
    } catch { /* non-JSON body, use fallback */ }
    throw new Error(detail)
  }
  // Server invalidated every refresh token; clear local state so the
  // in-memory access token cannot be used after the password rotation.
  useAuthStore.getState().clearAuth()
}
