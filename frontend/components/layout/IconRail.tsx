"use client"

import type { Route } from "next"
import Link from "next/link"
import { useRouter, usePathname } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { Workflow, LayoutGrid, User, Sun, Moon, ShieldCheck, LogOut } from "lucide-react"
import { useTheme } from "@/components/providers/ThemeProvider"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/lib/store/auth"
import { logout as apiLogout } from "@/lib/api/auth"
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
  const user = useAuthStore((s) => s.user)
  const queryClient = useQueryClient()

  async function handleLogout() {
    queryClient.clear()
    // Invalidates the refresh-token cookie + jti server-side, then clears
    // local state. Always navigates regardless of network outcome.
    await apiLogout()
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
          <RailLink
            icon={<LayoutGrid size={18} />}
            label="Assistants"
            href="/assistants"
          />
        )}

        <div className="flex-1" />

        {/* Footer icons */}
        {user?.is_admin && (
          <RailLink
            icon={<ShieldCheck size={18} />}
            label="Admin"
            href="/admin"
            active={pathname.startsWith("/admin")}
          />
        )}
        <RailLink
          icon={<User size={18} />}
          label="Profile"
          href="/profile"
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

const railButtonClass = (active?: boolean, danger?: boolean) =>
  cn(
    "w-10 h-10 rounded-md flex items-center justify-center transition-colors cursor-pointer no-underline",
    active
      ? "text-[#2a9d8f] bg-[#2a9d8f]/10"
      : danger
        ? "text-foreground/70 hover:text-red-400 hover:bg-red-400/15"
        : "text-foreground/80 hover:text-white hover:bg-white/10"
  )

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
        className={railButtonClass(active, danger)}
      >
        {icon}
      </TooltipTrigger>
      <TooltipContent side="right" className="text-xs">
        {label}
      </TooltipContent>
    </Tooltip>
  )
}

function RailLink({
  icon,
  label,
  href,
  active,
}: {
  icon: React.ReactNode
  label: string
  href: Route
  active?: boolean
}) {
  return (
    <Tooltip>
      {/* Base UI render prop: TooltipTrigger merges its ARIA/ref/handlers
          onto the provided <Link>, so middle-click + prefetch work natively. */}
      <TooltipTrigger
        render={<Link href={href} />}
        className={railButtonClass(active)}
      >
        {icon}
      </TooltipTrigger>
      <TooltipContent side="right" className="text-xs">
        {label}
      </TooltipContent>
    </Tooltip>
  )
}
