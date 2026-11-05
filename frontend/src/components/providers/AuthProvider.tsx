import { useEffect } from "react"
import { useAuthStore } from "@/lib/store/auth"
import { refreshSession } from "@/lib/api/auth"

export function AuthProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // On page reload Zustand state is empty. The refresh token lives in an
    // HttpOnly cookie we can't read from JS, so we just try /auth/refresh
    // and let it fail silently if there's no valid cookie.
    const { accessToken } = useAuthStore.getState()
    if (!accessToken) {
      refreshSession().catch(() => useAuthStore.getState().clearAuth())
    }
  }, [])

  return <>{children}</>
}
