"use client"

import { usePathname } from "next/navigation"
import { DualSidebar } from "@/components/layout/DualSidebar"

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isUtilityPage = pathname.startsWith("/profile") || pathname.startsWith("/admin")

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <DualSidebar />
      <main className={isUtilityPage ? "flex-1 overflow-auto flex items-start justify-center p-8" : "flex-1 overflow-hidden"}>
        {children}
      </main>
    </div>
  )
}
