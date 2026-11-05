import { Navigate, Outlet } from "react-router"
import { useAuthStore } from "@/lib/store/auth"

export function RequireAuth() {
  const accessToken = useAuthStore((s) => s.accessToken)
  return accessToken ? <Outlet /> : <Navigate to="/login" replace />
}

export function RequireGuest() {
  const accessToken = useAuthStore((s) => s.accessToken)
  return accessToken ? <Navigate to="/assistants" replace /> : <Outlet />
}
