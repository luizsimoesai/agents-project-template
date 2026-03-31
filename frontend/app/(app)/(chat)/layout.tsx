import { DualSidebar } from "@/components/layout/DualSidebar"

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <DualSidebar />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  )
}
