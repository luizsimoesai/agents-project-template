"use client"

import { useEffect } from "react"
import { useAuthStore } from "@/lib/store/auth"
import { refreshSession } from "@/lib/api/auth"

export function AuthProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // If cookie exists but Zustand store is empty (e.g., page reload),
    // attempt to rehydrate via refresh token
    const { accessToken } = useAuthStore.getState()
    if (!accessToken) {
      const refreshToken = localStorage.getItem("refresh_token")
      if (refreshToken) {
        refreshSession().catch(() => useAuthStore.getState().clearAuth())
      }
    }
  }, [])

  return <>{children}</>
}
