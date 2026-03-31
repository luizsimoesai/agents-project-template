"use client"

import { useAuthStore } from "@/lib/store/auth"
import { AdminUserTable } from "@/components/admin/AdminUserTable"
import { ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"

export default function AdminPage() {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)

  if (!user?.is_admin) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <ShieldCheck size={48} className="text-muted-foreground" />
        <p className="font-mono text-sm text-muted-foreground">restricted to administrators</p>
        <Button variant="outline" onClick={() => router.push("/assistants")}>go back</Button>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center gap-2 mb-6">
        <ShieldCheck size={20} style={{ color: "#136ddd" }} />
        <h1 className="text-xl font-mono font-semibold" style={{ color: "#136ddd" }}>
          admin / users
        </h1>
      </div>
      <AdminUserTable />
    </div>
  )
}
