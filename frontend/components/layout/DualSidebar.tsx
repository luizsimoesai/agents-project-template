"use client"

import { useState, useRef, useEffect } from "react"
import { useRouter, useParams, usePathname } from "next/navigation"
import { Plus, Trash2, Pencil, Check, X } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { useThreads, useDeleteThread, useUpdateThreadName } from "@/lib/hooks/useThreads"
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

function ThreadItem({
  t,
  isActive,
  onNavigate,
  onDelete,
}: {
  t: ThreadRead
  isActive: boolean
  onNavigate: () => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const updateName = useUpdateThreadName()

  function startEdit(e: React.MouseEvent) {
    e.stopPropagation()
    setDraft(t.metadata?.thread_name || "")
    setEditing(true)
  }

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  function cancel() {
    setEditing(false)
  }

  async function confirm(e?: React.MouseEvent) {
    e?.stopPropagation()
    const name = draft.trim()
    if (name && name !== t.metadata?.thread_name) {
      await updateName.mutateAsync({ id: t.thread_id, name })
    }
    setEditing(false)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") confirm()
    if (e.key === "Escape") cancel()
  }

  const label = t.metadata?.thread_name || `${t.thread_id.slice(0, 8)}…`

  return (
    <div
      className={cn(
        "group/thread w-full flex items-center gap-1 px-2 py-2 rounded-md text-[13px] transition-colors",
        isActive
          ? "bg-[#2a9d8f]/10 text-foreground font-semibold"
          : "text-foreground/75 hover:bg-white/10 hover:text-foreground"
      )}
    >
      {editing ? (
        <>
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            onClick={(e) => e.stopPropagation()}
            className="flex-1 min-w-0 bg-transparent border-b border-[#2a9d8f]/60 outline-none text-[13px] font-mono text-foreground py-0.5 pr-1"
          />
          <button
            type="button"
            onClick={confirm}
            className="shrink-0 w-5 h-5 flex items-center justify-center rounded text-[#2a9d8f] hover:bg-[#2a9d8f]/10"
          >
            <Check size={12} />
          </button>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); cancel() }}
            className="shrink-0 w-5 h-5 flex items-center justify-center rounded text-muted-foreground/60 hover:bg-white/10"
          >
            <X size={12} />
          </button>
        </>
      ) : (
        <>
          <button
            type="button"
            onClick={onNavigate}
            className="flex items-center gap-2 flex-1 min-w-0 text-left"
          >
            <div
              className={cn(
                "w-1.5 h-1.5 rounded-full shrink-0",
                isActive ? "bg-[#2a9d8f]" : "bg-muted-foreground/25"
              )}
            />
            <span className="truncate font-mono">{label}</span>
          </button>
          <button
            type="button"
            aria-label="Rename conversation"
            onClick={startEdit}
            className="shrink-0 opacity-0 group-hover/thread:opacity-100 transition-opacity w-6 h-6 flex items-center justify-center rounded text-muted-foreground/50 hover:text-foreground hover:bg-white/10"
          >
            <Pencil size={12} />
          </button>
          <button
            type="button"
            aria-label="Delete conversation"
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            className="shrink-0 opacity-0 group-hover/thread:opacity-100 transition-opacity w-6 h-6 flex items-center justify-center rounded text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10"
          >
            <Trash2 size={13} />
          </button>
        </>
      )}
    </div>
  )
}

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
  const deleteThread = useDeleteThread()
  const [deleteTarget, setDeleteTarget] = useState<ThreadRead | undefined>(undefined)

  function handleNewThread() {
    if (!assistantId) return
    router.push(`/assistants/${assistantId}/threads`)
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
          <div className="w-[220px] shrink-0 border-r border-border/60 bg-sidebar flex flex-col h-full">
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

            {/* New conversation */}
            <div className="px-2 pt-2 pb-1">
              <button
                type="button"
                onClick={handleNewThread}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-[13px] font-medium text-[#2a9d8f] border border-[#2a9d8f]/40 hover:bg-[#2a9d8f]/10 hover:border-[#2a9d8f]/60 transition-colors"
              >
                <Plus size={13} />
                <span>New conversation</span>
              </button>
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
                <ThreadItem
                  key={t.thread_id}
                  t={t}
                  isActive={threadId === t.thread_id}
                  onNavigate={() => router.push(`/assistants/${assistantId}/threads/${t.thread_id}`)}
                  onDelete={() => setDeleteTarget(t)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {deleteTarget && (
        <AlertDialog
          open
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
      )}
    </>
  )
}
