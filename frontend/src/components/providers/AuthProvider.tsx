import { useEffect, useState } from "react"
import { useAuthStore } from "@/lib/store/auth"
import { refreshSession } from "@/lib/api/auth"
import Loading from "@/routes/Loading"

// How long the routes wait for the initial refresh. The fetch itself is never
// aborted: if the server already rotated the token, losing its response would
// make the next refresh look like a replay and end the session.
const REFRESH_WAIT_MS = 8000

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(() => !!useAuthStore.getState().accessToken)

  useEffect(() => {
    // On page reload Zustand state is empty. The refresh token lives in an
    // HttpOnly cookie we can't read from JS, so we just try /auth/refresh and
    // hold the routes back until we know whether a session exists.
    if (useAuthStore.getState().accessToken) return
    const timer = setTimeout(() => setReady(true), REFRESH_WAIT_MS)
    refreshSession()
      .catch(() => {
        // A late failure must not end a login made while the routes were open.
        if (!useAuthStore.getState().accessToken) useAuthStore.getState().clearAuth()
      })
      .finally(() => {
        clearTimeout(timer)
        setReady(true)
      })
    return () => clearTimeout(timer)
  }, [])

  if (!ready) return <Loading />

  return <>{children}</>
}
