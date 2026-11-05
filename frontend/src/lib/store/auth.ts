import { create } from "zustand"
import type { UserRead } from "@/lib/types"

interface AuthStore {
  accessToken: string | null
  user: UserRead | null
  setAuth: (token: string, user: UserRead) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: null,
  user: null,
  setAuth: (token, user) => set({ accessToken: token, user }),
  clearAuth: () => {
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
