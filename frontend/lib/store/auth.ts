import { create } from "zustand"
import type { UserRead } from "@/lib/types"

const COOKIE_NAME = "access_token"

function setCookie(value: string) {
  document.cookie = `${COOKIE_NAME}=${value};path=/;SameSite=Lax`
}

function removeCookie() {
  document.cookie = `${COOKIE_NAME}=;path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT`
}

interface AuthStore {
  accessToken: string | null
  user: UserRead | null
  setAuth: (token: string, user: UserRead) => void  // also writes access_token cookie
  clearAuth: () => void                              // also removes cookie and localStorage
}

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: null,
  user: null,
  setAuth: (token, user) => {
    setCookie(token)
    set({ accessToken: token, user })
  },
  clearAuth: () => {
    removeCookie()
    try {
      localStorage.removeItem("refresh_token")
    } catch {
      // localStorage may not be available in all environments
    }
    set({ accessToken: null, user: null })
  },
}))
