"use client"

import { useState } from "react"
import { useRouter, useParams, usePathname } from "next/navigation"
import { Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { useThreads, useCreateThread, useDeleteThread } from "@/lib/hooks/useThreads"
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from "@/components/ui/alert-dialog"
import type { ThreadRead } from "@/lib/types"
import { IconRail } from "./IconRail"

export function DualSidebar() {
  const router = useRouter()
  const params = useParams()
  const pathname = usePathname()

  const assistantId = params.id as string | undefined
  const threadId = params.threadId as string | undefined
  const isUtilityPage = pathname.startsWith("/profile") || pathname.startsWith("/admin")

  const { data: assistants } = useAssistants()
  const assistant = assistants?.find((a) => a.assistant_id === assistantId)
  const { data: threads } = useThreads(assistantId)
  const createThread = useCreateThread()
  const deleteThread = useDeleteThread()
  const [deleteTarget, setDeleteTarget] = useState<ThreadRead | undefined>(undefined)

  async function handleNewThread() {
    if (!assistantId) return
    try {
      const t = await createThread.mutateAsync({ assistant_id: assistantId })
      router.push(`/assistants/${assistantId}/threads/${t.thread_id}`)
    } catch {
      toast.error("Failed to create conversation")
    }
  }

  async function handleDeleteThread() {
    if (!deleteTarget) return
    try {
      await deleteThread.mutateAsync(deleteTarget.thread_id)
      toast.success("Conversation deleted")
      if (threadId === deleteTarget.thread_id) {
        router.push(`/assistants/${assistantId}/threads`)
      }
      setDeleteTarget(undefined)
    } catch {
      toast.error("Failed to delete conversation")
    }
  }

  return (
    <>
      <div className="flex h-full shrink-0">
        <IconRail />

        {/* Wide panel — hidden on utility pages (profile, admin) */}
        {!isUtilityPage && (
          <div className="w-[180px] shrink-0 border-r border-border/60 bg-sidebar flex flex-col h-full">
            {/* Assistant name + description */}
            <div className="px-3 pt-3 pb-2 border-b border-border/40">
              <p className="text-[15px] font-semibold text-foreground truncate">
                {assistant?.name ?? ""}
              </p>
              {assistant?.description && (
                <p className="text-[13px] text-foreground/70 mt-1 line-clamp-3">
                  {assistant.description}
                </p>
              )}
            </div>

            {/* Thread list */}
            <div className="flex-1 overflow-y-auto py-2 px-2">
              <p className="px-2 py-1 text-[10px] font-mono uppercase tracking-[0.2em] text-foreground/50 select-none">
                Conversations
              </p>
              {threads?.length === 0 && (
                <p className="px-2 py-3 text-xs text-foreground/60 font-mono text-center">
                  No conversations yet.
                </p>
              )}
              {threads?.map((t) => (
                <div
                  key={t.thread_id}
                  className={cn(
                    "group/thread w-full flex items-center gap-2 px-2 py-2 rounded-md text-[13px] transition-colors",
                    threadId === t.thread_id
                      ? "bg-[#2a9d8f]/10 text-[#c0d8ff]"
                      : "text-foreground/75 hover:bg-white/10 hover:text-white"
                  )}
                >
                  <button
                    type="button"
                    onClick={() =>
                      router.push(`/assistants/${assistantId}/threads/${t.thread_id}`)
                    }
                    className="flex items-center gap-2 flex-1 min-w-0 text-left"
                  >
                    <div
                      className={cn(
                        "w-1.5 h-1.5 rounded-full shrink-0",
                        threadId === t.thread_id
                          ? "bg-[#2a9d8f]"
                          : "bg-muted-foreground/25"
                      )}
                    />
                    <span className="truncate font-mono">
                      {t.metadata?.thread_name || `${t.thread_id.slice(0, 8)}…`}
                    </span>
                  </button>
                  <button
                    type="button"
                    aria-label="Delete conversation"
                    onClick={(e) => { e.stopPropagation(); setDeleteTarget(t) }}
                    className="shrink-0 opacity-0 group-hover/thread:opacity-100 transition-opacity w-6 h-6 flex items-center justify-center rounded text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>

            {/* New conversation */}
            <div className="p-2 border-t border-border/40">
              <button
                type="button"
                onClick={handleNewThread}
                disabled={createThread.isPending}
                className="w-full flex items-center gap-2 px-2 py-2 border border-dashed border-border/40 rounded-md text-[13px] text-foreground/70 hover:text-white hover:border-[#2a9d8f]/40 hover:bg-white/10 transition-colors disabled:opacity-40"
              >
                <Plus size={12} />
                <span>New conversation</span>
              </button>
            </div>
          </div>
        )}
      </div>

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => { if (!open) setDeleteTarget(undefined) }}
      >
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete conversation</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this conversation? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteThread}
              disabled={deleteThread.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteThread.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
