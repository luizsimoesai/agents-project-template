import { create } from "zustand"
import type { UserRead } from "@/lib/types"

const COOKIE_NAME = "access_token"

// NOTE: This cookie is intentionally NOT HttpOnly so Next.js middleware can read it
// for route protection AND the client can set/clear it. This means it is accessible
// to JavaScript — an accepted trade-off for this architecture. Mitigate XSS risk
// by using CSP headers and never storing sensitive data beyond the JWT token.
function setCookie(value: string, expiresIn?: number) {
  if (typeof document === "undefined") return
  const maxAge = expiresIn ? `;Max-Age=${expiresIn}` : ""
  document.cookie = `${COOKIE_NAME}=${value};path=/;SameSite=Lax${maxAge}`
}

function removeCookie() {
  if (typeof document === "undefined") return
  document.cookie = `${COOKIE_NAME}=;path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT`
}

interface AuthStore {
  accessToken: string | null
  user: UserRead | null
  setAuth: (token: string, user: UserRead, expiresIn?: number) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: null,
  user: null,
  setAuth: (token, user, expiresIn) => {
    setCookie(token, expiresIn)
    set({ accessToken: token, user })
  },
  clearAuth: () => {
    removeCookie()
    // Best-effort: legacy installs may still have a refresh_token in
    // localStorage from before the HttpOnly cookie migration. Clearing it
    // here ensures those orphaned values disappear on logout / 401.
    try {
      localStorage.removeItem("refresh_token")
    } catch {
      // localStorage may not be available in all environments
    }
    set({ accessToken: null, user: null })
  },
}))
