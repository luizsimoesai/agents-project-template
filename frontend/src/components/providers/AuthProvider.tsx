import { useEffect, useState } from "react"
import { useAuthStore } from "@/lib/store/auth"
import { refreshSession } from "@/lib/api/auth"
import Loading from "@/routes/Loading"

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(() => !!useAuthStore.getState().accessToken)

  useEffect(() => {
    // On page reload Zustand state is empty. The refresh token lives in an
    // HttpOnly cookie we can't read from JS, so we just try /auth/refresh and
    // hold the routes back until we know whether a session exists.
    if (useAuthStore.getState().accessToken) return
    refreshSession()
      .catch(() => useAuthStore.getState().clearAuth())
      .finally(() => setReady(true))
  }, [])

  if (!ready) return <Loading />

  return <>{children}</>
}
