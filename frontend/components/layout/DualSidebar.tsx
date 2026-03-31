"use client"

import { useRouter, useParams, usePathname } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { Bot, LayoutGrid, User, Sun, Moon, ShieldCheck, LogOut, Plus } from "lucide-react"
import { useTheme } from "next-themes"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/lib/store/auth"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { useThreads, useCreateThread } from "@/lib/hooks/useThreads"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export function DualSidebar() {
  const router = useRouter()
  const params = useParams()
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { user, clearAuth } = useAuthStore()
  const queryClient = useQueryClient()

  const assistantId = params.id as string | undefined
  const threadId = params.threadId as string | undefined

  const { data: assistants } = useAssistants()
  const assistant = assistants?.find((a) => a.assistant_id === assistantId)
  const { data: threads } = useThreads(assistantId)
  const createThread = useCreateThread()

  async function handleNewThread() {
    if (!assistantId) return
    try {
      const t = await createThread.mutateAsync({ assistant_id: assistantId })
      router.push(`/assistants/${assistantId}/threads/${t.thread_id}`)
    } catch {
      toast.error("Failed to create conversation")
    }
  }

  function handleLogout() {
    queryClient.clear()
    clearAuth()
    router.push("/login")
  }

  return (
    <div className="flex h-full shrink-0">
      {/* Icon rail — 44px */}
      <TooltipProvider delayDuration={300}>
        <div className="w-11 shrink-0 border-r border-border/60 bg-sidebar flex flex-col items-center py-2 gap-1">
          {/* App logo */}
          <div className="w-7 h-7 rounded-md bg-[#136ddd] flex items-center justify-center mb-2 shrink-0">
            <Bot size={14} className="text-white" />
          </div>

          {/* Back to assistant picker */}
          <RailButton
            icon={<LayoutGrid size={14} />}
            label="Assistants"
            onClick={() => router.push("/assistants")}
          />

          <div className="flex-1" />

          {/* Footer icons */}
          {user?.is_admin && (
            <RailButton
              icon={<ShieldCheck size={14} />}
              label="Admin"
              onClick={() => router.push("/admin")}
              active={pathname.startsWith("/admin")}
            />
          )}
          <RailButton
            icon={<User size={14} />}
            label="Profile"
            onClick={() => router.push("/profile")}
            active={pathname.startsWith("/profile")}
          />
          <RailButton
            icon={theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
            label={theme === "dark" ? "Light theme" : "Dark theme"}
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          />
          <RailButton
            icon={<LogOut size={14} />}
            label="Logout"
            onClick={handleLogout}
            danger
          />
        </div>
      </TooltipProvider>

      {/* Wide panel — 180px */}
      <div className="w-[180px] shrink-0 border-r border-border/60 bg-sidebar flex flex-col h-full">
        {/* Assistant name + description */}
        <div className="px-3 pt-3 pb-2 border-b border-border/40">
          <p className="text-sm font-semibold text-foreground truncate">
            {assistant?.name ?? ""}
          </p>
          {assistant?.description && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
              {assistant.description}
            </p>
          )}
        </div>

        {/* Thread list */}
        <div className="flex-1 overflow-y-auto py-2 px-2">
          <p className="px-2 py-1 text-[9px] font-mono uppercase tracking-[0.2em] text-muted-foreground/40 select-none">
            Conversations
          </p>
          {threads?.length === 0 && (
            <p className="px-2 py-3 text-xs text-muted-foreground/40 font-mono text-center">
              No conversations yet.
            </p>
          )}
          {threads?.map((t) => (
            <button
              key={t.thread_id}
              type="button"
              onClick={() =>
                router.push(`/assistants/${assistantId}/threads/${t.thread_id}`)
              }
              className={cn(
                "w-full text-left flex items-center gap-2 px-2 py-2 rounded-md text-xs transition-colors",
                threadId === t.thread_id
                  ? "bg-[#136ddd]/10 text-[#c0d8ff]"
                  : "text-muted-foreground/70 hover:bg-accent hover:text-foreground"
              )}
            >
              <div
                className={cn(
                  "w-1.5 h-1.5 rounded-full shrink-0",
                  threadId === t.thread_id
                    ? "bg-[#136ddd]"
                    : "bg-muted-foreground/25"
                )}
              />
              <span className="truncate font-mono">
                {t.thread_name ?? `${t.thread_id.slice(0, 8)}…`}
              </span>
            </button>
          ))}
        </div>

        {/* New conversation */}
        <div className="p-2 border-t border-border/40">
          <button
            type="button"
            onClick={handleNewThread}
            disabled={createThread.isPending}
            className="w-full flex items-center gap-2 px-2 py-2 border border-dashed border-border/40 rounded-md text-xs text-muted-foreground/50 hover:text-foreground hover:border-[#136ddd]/40 hover:bg-[#136ddd]/5 transition-colors disabled:opacity-40"
          >
            <Plus size={12} />
            <span>New conversation</span>
          </button>
        </div>
      </div>
    </div>
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
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={onClick}
          className={cn(
            "w-8 h-8 rounded-md flex items-center justify-center transition-colors",
            active
              ? "text-[#136ddd] bg-[#136ddd]/10"
              : danger
                ? "text-muted-foreground/40 hover:text-red-400 hover:bg-red-500/10"
                : "text-muted-foreground/40 hover:text-foreground hover:bg-accent"
          )}
        >
          {icon}
        </button>
      </TooltipTrigger>
      <TooltipContent side="right" className="text-xs">
        {label}
      </TooltipContent>
    </Tooltip>
  )
}
