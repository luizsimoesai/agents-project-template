"use client"

import { useRouter, usePathname } from "next/navigation"
import {
  LayoutList,
  User,
  Sun,
  Moon,
  ShieldCheck,
  LogOut,
} from "lucide-react"
import { useTheme } from "next-themes"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/lib/store/auth"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

const BRAND = "#136ddd"

interface NavIconProps {
  icon: React.ReactNode
  label: string
  active: boolean
  onClick?: () => void
}

function NavIcon({ icon, label, active, onClick }: NavIconProps) {
  return (
    <TooltipProvider delay={300}>
      <Tooltip>
        <TooltipTrigger
          onClick={onClick}
          className={cn(
            "w-9 h-9 flex items-center justify-center rounded-md transition-colors cursor-pointer",
            active
              ? "bg-[#136ddd]/10 text-[#136ddd]"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          )}
        >
          {icon}
        </TooltipTrigger>
        <TooltipContent side="right">{label}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

export function AppSidebar() {
  const router = useRouter()
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { user, clearAuth } = useAuthStore()

  const isActive = (prefix: string) => pathname.startsWith(prefix)

  function handleLogout() {
    clearAuth()
    router.push("/login")
  }

  return (
    <div className="w-[52px] border-r border-border bg-card flex flex-col items-center py-3 gap-1 flex-shrink-0">
      {/* Logo */}
      <div
        className="w-7 h-7 rounded-md mb-3 flex items-center justify-center text-white text-xs font-mono font-bold"
        style={{ backgroundColor: BRAND }}
      >
        λ
      </div>

      <NavIcon
        icon={<LayoutList size={16} />}
        label="Assistentes"
        active={isActive("/assistants")}
        onClick={() => router.push("/assistants")}
      />

      <NavIcon
        icon={<User size={16} />}
        label="Perfil"
        active={isActive("/profile")}
        onClick={() => router.push("/profile")}
      />

      <NavIcon
        icon={theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        label="Alternar tema"
        active={false}
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      />

      {user?.is_admin && (
        <NavIcon
          icon={<ShieldCheck size={16} />}
          label="Admin"
          active={isActive("/admin")}
          onClick={() => router.push("/admin")}
        />
      )}

      <div className="flex-1" />

      <NavIcon
        icon={<LogOut size={16} />}
        label="Sair"
        active={false}
        onClick={handleLogout}
      />
    </div>
  )
}
