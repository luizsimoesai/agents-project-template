"use client"

import { useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { Workflow, LayoutGrid, User, Sun, Moon, ShieldCheck, LogOut } from "lucide-react"
import { useTheme } from "@/components/providers/ThemeProvider"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/lib/store/auth"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export function IconRail() {
  const router = useRouter()
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { user, clearAuth } = useAuthStore()
  const queryClient = useQueryClient()

  function handleLogout() {
    queryClient.clear()
    clearAuth()
    router.push("/login")
  }

  const isOnAssistants = pathname === "/assistants"

  return (
    <TooltipProvider delay={300}>
      <div className="w-14 shrink-0 border-r border-border/60 bg-sidebar flex flex-col items-center py-2 gap-1">
        {/* App logo */}
        <div className="w-9 h-9 rounded-md bg-[#2a9d8f] flex items-center justify-center mb-2 shrink-0">
          <Workflow size={18} className="text-white" />
        </div>

        {/* Back to assistants (hidden when already on assistants) */}
        {!isOnAssistants && (
          <RailButton
            icon={<LayoutGrid size={18} />}
            label="Assistants"
            onClick={() => router.push("/assistants")}
          />
        )}

        <div className="flex-1" />

        {/* Footer icons */}
        {user?.is_admin && (
          <RailButton
            icon={<ShieldCheck size={18} />}
            label="Admin"
            onClick={() => router.push("/admin")}
            active={pathname.startsWith("/admin")}
          />
        )}
        <RailButton
          icon={<User size={18} />}
          label="Profile"
          onClick={() => router.push("/profile")}
          active={pathname.startsWith("/profile")}
        />
        <RailButton
          icon={theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          label={theme === "dark" ? "Light theme" : "Dark theme"}
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        />
        <RailButton
          icon={<LogOut size={18} />}
          label="Logout"
          onClick={handleLogout}
          danger
        />
      </div>
    </TooltipProvider>
  )
}

function RailButton({
  icon,
  label,
  onClick,
  active,
  danger,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  active?: boolean
  danger?: boolean
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        type="button"
        onClick={onClick}
        className={cn(
          "w-10 h-10 rounded-md flex items-center justify-center transition-colors cursor-pointer",
          active
            ? "text-[#2a9d8f] bg-[#2a9d8f]/10"
            : danger
              ? "text-foreground/70 hover:text-red-400 hover:bg-red-400/15"
              : "text-foreground/80 hover:text-white hover:bg-white/10"
        )}
      >
        {icon}
      </TooltipTrigger>
      <TooltipContent side="right" className="text-xs">
        {label}
      </TooltipContent>
    </Tooltip>
  )
}
