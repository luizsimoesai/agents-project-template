"use client"

import { useParams, usePathname, useRouter } from "next/navigation"
import { Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useAssistants, useDeleteAssistant } from "@/lib/hooks/useAssistants"
import { useThreads, useCreateThread, useDeleteThread } from "@/lib/hooks/useThreads"
import { AssistantForm } from "@/components/assistants/AssistantForm"
import { useState } from "react"
import { cn } from "@/lib/utils"

export function ContextPanel() {
  const pathname = usePathname()
  const params = useParams()
  const assistantId = params.id as string | undefined
  const threadId = params.threadId as string | undefined

  const isAdmin = pathname.startsWith("/admin")

  if (isAdmin) return <AdminPanel />
  if (assistantId) return <ThreadsPanel assistantId={assistantId} activeThreadId={threadId} />
  return <AssistantsPanel />
}

function AssistantsPanel() {
  const router = useRouter()
  const params = useParams()
  const { data: assistants, isLoading } = useAssistants()
  const deleteAssistant = useDeleteAssistant()
  const [formOpen, setFormOpen] = useState(false)
  const activeId = params.id as string | undefined

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation()
    try {
      await deleteAssistant.mutateAsync(id)
      toast.success("Assistente apagado")
      if (activeId === id) router.push("/assistants")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao apagar assistente")
    }
  }

  return (
    <div className="w-[220px] border-r border-border bg-background flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-3 border-b border-border">
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          assistentes
        </span>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setFormOpen(true)}>
          <Plus size={12} />
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full rounded-md" />
            ))
          : assistants?.map((a) => (
              <div
                key={a.assistant_id}
                onClick={() => router.push(`/assistants/${a.assistant_id}/threads`)}
                className={cn(
                  "flex items-center justify-between px-2 py-1.5 rounded-md cursor-pointer group text-sm",
                  activeId === a.assistant_id
                    ? "bg-[#136ddd]/10 text-[#136ddd]"
                    : "hover:bg-accent text-foreground"
                )}
              >
                <span className="truncate">{a.name}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 opacity-0 group-hover:opacity-100"
                  onClick={(e) => handleDelete(e, a.assistant_id)}
                >
                  <Trash2 size={10} />
                </Button>
              </div>
            ))}
      </div>
      <AssistantForm open={formOpen} onClose={() => setFormOpen(false)} />
    </div>
  )
}

function ThreadsPanel({
  assistantId,
  activeThreadId,
}: {
  assistantId: string
  activeThreadId?: string
}) {
  const router = useRouter()
  const { data: threads, isLoading } = useThreads(assistantId)
  const createThread = useCreateThread()
  const deleteThread = useDeleteThread()

  async function handleNew() {
    const t = await createThread.mutateAsync({ assistant_id: assistantId })
    router.push(`/assistants/${assistantId}/threads/${t.thread_id}`)
  }

  async function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation()
    try {
      await deleteThread.mutateAsync(id)
      toast.success("Conversa apagada")
      if (activeThreadId === id) router.push(`/assistants/${assistantId}/threads`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao apagar conversa")
    }
  }

  return (
    <div className="w-[220px] border-r border-border bg-background flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-3 border-b border-border">
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          conversas
        </span>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleNew}>
          <Plus size={12} />
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full rounded-md" />
            ))
          : threads?.map((t) => (
              <div
                key={t.thread_id}
                onClick={() =>
                  router.push(`/assistants/${assistantId}/threads/${t.thread_id}`)
                }
                className={cn(
                  "flex items-center justify-between px-2 py-1.5 rounded-md cursor-pointer group text-sm",
                  activeThreadId === t.thread_id
                    ? "bg-[#136ddd]/10 text-[#136ddd]"
                    : "hover:bg-accent text-foreground"
                )}
              >
                <span className="truncate font-mono text-xs">
                  {t.thread_name ?? t.thread_id.slice(0, 8) + "..."}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 opacity-0 group-hover:opacity-100"
                  onClick={(e) => handleDelete(e, t.thread_id)}
                >
                  <Trash2 size={10} />
                </Button>
              </div>
            ))}
      </div>
    </div>
  )
}

function AdminPanel() {
  return (
    <div className="w-[220px] border-r border-border bg-background flex flex-col h-full">
      <div className="px-3 py-3 border-b border-border">
        <span className="text-[10px] font-mono uppercase tracking-widest text-[#136ddd]">
          admin / usuários
        </span>
      </div>
      <div className="p-3 text-xs text-muted-foreground font-mono">
        Gerenciar usuários →
      </div>
    </div>
  )
}
