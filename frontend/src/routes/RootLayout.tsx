import { Outlet } from "react-router"
import { ThemeProvider } from "@/components/providers/ThemeProvider"
import { Toaster } from "sonner"
import { QueryProvider } from "@/components/providers/QueryProvider"
import { AuthProvider } from "@/components/providers/AuthProvider"

export default function RootLayout() {
  return (
    <ThemeProvider>
      <QueryProvider>
        <AuthProvider>
          <Outlet />
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </QueryProvider>
    </ThemeProvider>
  )
}
