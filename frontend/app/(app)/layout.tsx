import { AppSidebar } from "@/components/layout/AppSidebar"

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AppSidebar />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  )
}
