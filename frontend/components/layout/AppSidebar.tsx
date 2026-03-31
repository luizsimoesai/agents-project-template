"use client"

import { useState } from "react"
import { useRouter, usePathname, useParams } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import {
  Bot, Sun, Moon, LayoutGrid, User, ShieldCheck, LogOut, ChevronDown,
} from "lucide-react"
import { useTheme } from "next-themes"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/lib/store/auth"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { useThreads, useCreateThread } from "@/lib/hooks/useThreads"

export function AppSidebar() {
  const router = useRouter()
  const pathname = usePathname()
  const params = useParams()
  const { theme, setTheme } = useTheme()
  const { user, clearAuth } = useAuthStore()
  const queryClient = useQueryClient()

  const urlAssistantId = params.id as string | undefined
  const urlThreadId = params.threadId as string | undefined
  const [localAssistantId, setLocalAssistantId] = useState<string | undefined>(undefined)

  const { data: assistants } = useAssistants()
  const selectedId = urlAssistantId ?? localAssistantId ?? assistants?.[0]?.assistant_id
  const { data: threads } = useThreads(selectedId)
  const createThread = useCreateThread()

  async function handleNewThread() {
    if (!selectedId) {
      toast.error("Selecione um assistant primeiro")
      return
    }
    try {
      const t = await createThread.mutateAsync({ assistant_id: selectedId })
      router.push(`/assistants/${selectedId}/threads/${t.thread_id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao criar conversa")
    }
  }

  function handleChangeAssistant(id: string) {
    setLocalAssistantId(id)
    router.push(`/assistants/${id}/threads`)
  }

  function handleLogout() {
    queryClient.clear()
    clearAuth()
    router.push("/login")
  }

  return (
    <div className="w-60 shrink-0 border-r border-border/60 bg-sidebar flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/60">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-[#136ddd] flex items-center justify-center shrink-0">
            <Bot size={13} className="text-white" />
          </div>
          <span className="text-sm font-semibold text-foreground">Agent Chat</span>
        </div>
        <button
          onClick={handleNewThread}
          disabled={!selectedId || createThread.isPending}
          className="text-xs px-2 py-1 rounded-md bg-[#136ddd] text-white hover:bg-[#136ddd]/80 transition-colors disabled:opacity-40"
        >
          + nova
        </button>
      </div>

      {/* Assistant dropdown */}
      <div className="px-3 py-2 border-b border-border/40">
        <div className="relative">
          <select
            value={selectedId ?? ""}
            onChange={(e) => handleChangeAssistant(e.target.value)}
            className="w-full bg-accent/40 border border-border/60 rounded-md px-3 py-1.5 text-xs font-mono text-foreground appearance-none cursor-pointer focus:outline-none focus:border-[#136ddd]/50 focus:ring-1 focus:ring-[#136ddd]/20 transition-colors"
          >
            {assistants?.map((a) => (
              <option key={a.assistant_id} value={a.assistant_id}>
                {a.name}
              </option>
            ))}
          </select>
          <ChevronDown
            size={11}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
          />
        </div>
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto py-1.5 px-2">
        <p className="px-2 py-1.5 text-[9px] font-mono uppercase tracking-[0.2em] text-muted-foreground/40 select-none">
          conversas
        </p>
        {threads?.length === 0 && (
          <p className="px-2 py-3 text-xs text-muted-foreground/40 font-mono text-center">
            Nenhuma conversa ainda.
          </p>
        )}
        {threads?.map((t) => (
          <button
            key={t.thread_id}
            type="button"
            onClick={() =>
              router.push(`/assistants/${selectedId}/threads/${t.thread_id}`)
            }
            className={cn(
              "w-full text-left flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer text-xs transition-colors",
              urlThreadId === t.thread_id
                ? "bg-[#136ddd]/10 text-[#c0d8ff]"
                : "text-muted-foreground/70 hover:bg-accent hover:text-foreground"
            )}
          >
            <div
              className={cn(
                "w-1.5 h-1.5 rounded-full shrink-0",
                urlThreadId === t.thread_id ? "bg-[#136ddd]" : "bg-muted-foreground/25"
              )}
            />
            <span className="truncate font-mono">
              {`${t.thread_name ?? `${t.thread_id.slice(0, 8)}…`}`}
            </span>
          </button>
        ))}
      </div>

      {/* Footer nav */}
      <div className="border-t border-border/60 p-2 space-y-px">
        {/* Exact match: only active on /assistants management page, not during chat sessions */}
        <FooterItem
          label="Assistants"
          icon={<LayoutGrid size={13} />}
          active={pathname === "/assistants"}
          onClick={() => router.push("/assistants")}
        />
        <FooterItem
          label="Perfil"
          icon={<User size={13} />}
          active={pathname.startsWith("/profile")}
          onClick={() => router.push("/profile")}
        />
        <FooterItem
          label={theme === "dark" ? "Tema claro" : "Tema escuro"}
          icon={theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        />
        {user?.is_admin && (
          <FooterItem
            label="Admin"
            icon={<ShieldCheck size={13} />}
            active={pathname.startsWith("/admin")}
            onClick={() => router.push("/admin")}
          />
        )}
        <FooterItem
          label="Sair"
          icon={<LogOut size={13} />}
          onClick={handleLogout}
          danger
        />
      </div>
    </div>
  )
}

function FooterItem({
  label,
  icon,
  active,
  onClick,
  danger,
}: {
  label: string
  icon: React.ReactNode
  active?: boolean
  onClick?: () => void
  danger?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-xs transition-colors text-left",
        active
          ? "text-[#136ddd] bg-[#136ddd]/10"
          : danger
            ? "text-muted-foreground/50 hover:text-red-400 hover:bg-red-500/10"
            : "text-muted-foreground/50 hover:text-foreground hover:bg-accent"
      )}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}
