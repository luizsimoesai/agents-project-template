import { AppSidebar } from "@/components/layout/AppSidebar"
import { ContextPanel } from "@/components/layout/ContextPanel"

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AppSidebar />
      <ContextPanel />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  )
}
