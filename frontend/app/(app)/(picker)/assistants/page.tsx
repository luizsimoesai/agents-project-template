"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Bot, Pencil, Trash2, Plus } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { useAssistants, useDeleteAssistant } from "@/lib/hooks/useAssistants"
import { AssistantForm } from "@/components/assistants/AssistantForm"
import type { AssistantRead } from "@/lib/types"

export default function AssistantPickerPage() {
  const router = useRouter()
  const { data: assistants, isLoading } = useAssistants()
  const deleteAssistant = useDeleteAssistant()
  const [formOpen, setFormOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<AssistantRead | undefined>(undefined)

  function openCreate() {
    setEditTarget(undefined)
    setFormOpen(true)
  }

  function openEdit(a: AssistantRead) {
    setEditTarget(a)
    setFormOpen(true)
  }

  async function handleDelete(id: string) {
    try {
      await deleteAssistant.mutateAsync(id)
      toast.success("Assistant deleted")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete assistant")
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* App header */}
      <header className="flex items-center gap-2.5 px-6 py-3 border-b border-border/60 shrink-0">
        <div className="w-6 h-6 rounded-md bg-[#136ddd] flex items-center justify-center shrink-0">
          <Bot size={13} className="text-white" />
        </div>
        <span className="text-sm font-semibold text-foreground">Agent Chat</span>
      </header>

      {/* Main content */}
      <main className="flex-1 p-8 max-w-5xl w-full mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-foreground">Assistants</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Select an assistant to start a conversation
          </p>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-lg" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3">
            {assistants?.map((a) => (
              <div
                key={a.assistant_id}
                role="button"
                tabIndex={0}
                onClick={() => router.push(`/assistants/${a.assistant_id}/threads`)}
                onKeyDown={(e) =>
                  e.key === "Enter" &&
                  router.push(`/assistants/${a.assistant_id}/threads`)
                }
                className="group relative bg-card border border-border/60 rounded-lg p-3 text-left cursor-pointer hover:border-[#136ddd]/50 hover:bg-[#136ddd]/5 transition-colors"
              >
                {/* Edit / delete — appear on hover */}
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); openEdit(a) }}
                    className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent"
                  >
                    <Pencil size={11} />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); handleDelete(a.assistant_id) }}
                    className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>

                {/* Bot icon */}
                <div className="w-8 h-8 rounded-md bg-[#136ddd] flex items-center justify-center mb-2 shrink-0">
                  <Bot size={16} className="text-white" />
                </div>

                {/* Name */}
                <p className="text-xs font-semibold text-foreground truncate">
                  {a.name}
                </p>

                {/* Description */}
                {a.description && (
                  <p className="text-[10px] text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
                    {a.description}
                  </p>
                )}
              </div>
            ))}

            {/* New assistant card */}
            <button
              type="button"
              onClick={openCreate}
              className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-border/40 rounded-lg p-3 min-h-[7rem] hover:border-[#136ddd]/40 hover:bg-[#136ddd]/5 transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center">
                <Plus size={16} className="text-muted-foreground" />
              </div>
              <span className="text-xs text-muted-foreground">New assistant</span>
            </button>
          </div>
        )}
      </main>

      <AssistantForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        assistant={editTarget}
      />
    </div>
  )
}
