"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Bot, Pencil, Trash2, Plus } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { useAssistants, useDeleteAssistant } from "@/lib/hooks/useAssistants"
import { AssistantForm } from "@/components/assistants/AssistantForm"
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
import type { AssistantRead } from "@/lib/types"
import { useAuthStore } from "@/lib/store/auth"
import { getGraphType } from "@/lib/graph-types"

export default function AssistantPickerPage() {
  const router = useRouter()
  const { data: assistants, isLoading } = useAssistants()
  const deleteAssistant = useDeleteAssistant()
  const user = useAuthStore((s) => s.user)
  const [formOpen, setFormOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<AssistantRead | undefined>(undefined)
  const [deleteTarget, setDeleteTarget] = useState<AssistantRead | undefined>(undefined)

  function openCreate() {
    setEditTarget(undefined)
    setFormOpen(true)
  }

  function openEdit(a: AssistantRead) {
    setEditTarget(a)
    setFormOpen(true)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      await deleteAssistant.mutateAsync(deleteTarget.assistant_id)
      toast.success("Assistant deleted")
      setDeleteTarget(undefined)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete assistant")
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <main className="flex-1 p-8 max-w-5xl w-full mx-auto">
        <div className="mb-6">
          {user?.name && (
            <p className="text-sm text-muted-foreground mb-1">Hello, {user.name}</p>
          )}
          <h1 className="text-xl font-bold text-foreground">Assistants</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Select an assistant to start a conversation
          </p>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-40 rounded-lg" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
            {assistants?.map((a) => (
              <div
                key={a.assistant_id}
                role="button"
                tabIndex={0}
                aria-label={`Select ${a.name}`}
                onClick={() => router.push(`/assistants/${a.assistant_id}/threads`)}
                onKeyDown={(e) =>
                  e.key === "Enter" &&
                  router.push(`/assistants/${a.assistant_id}/threads`)
                }
                className="group relative bg-card border border-border/60 rounded-lg p-5 text-left cursor-pointer hover:border-[#2a9d8f]/50 hover:bg-[#2a9d8f]/5 transition-colors min-h-40"
              >
                {/* Edit / delete — appear on hover */}
                <div className="absolute top-3 right-3 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    type="button"
                    aria-label="Edit assistant"
                    onClick={(e) => { e.stopPropagation(); openEdit(a) }}
                    className="w-7 h-7 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent"
                  >
                    <Pencil size={15} />
                  </button>
                  <button
                    type="button"
                    aria-label="Delete assistant"
                    onClick={(e) => { e.stopPropagation(); setDeleteTarget(a) }}
                    className="w-7 h-7 rounded flex items-center justify-center text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>

                {/* Bot icon */}
                <div className="w-10 h-10 rounded-md bg-[#2a9d8f] flex items-center justify-center mb-3 shrink-0">
                  <Bot size={20} className="text-white" />
                </div>

                {/* Name */}
                <p className="text-base font-semibold text-foreground truncate">
                  {a.name}
                </p>

                {/* Description */}
                {a.description && (
                  <p className="text-sm text-muted-foreground mt-1.5 line-clamp-3 leading-relaxed">
                    {a.description}
                  </p>
                )}

                {/* Graph type badge */}
                <span className="inline-block mt-2 px-2 py-0.5 rounded text-xs bg-accent text-muted-foreground">
                  {getGraphType(a.graph_id)?.label ?? a.graph_id}
                </span>
              </div>
            ))}

            {/* New assistant card */}
            <button
              type="button"
              onClick={openCreate}
              className="flex flex-col items-center justify-center gap-3 border-2 border-dashed border-border/40 rounded-lg p-5 min-h-40 hover:border-[#2a9d8f]/40 hover:bg-[#2a9d8f]/5 transition-colors"
            >
              <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center">
                <Plus size={20} className="text-muted-foreground" />
              </div>
              <span className="text-base text-muted-foreground">New assistant</span>
            </button>
          </div>
        )}
      </main>

      <AssistantForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        assistant={editTarget}
      />

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => { if (!open) setDeleteTarget(undefined) }}
      >
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete assistant</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &ldquo;{deleteTarget?.name}&rdquo;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteAssistant.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteAssistant.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
