"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Pencil, Trash2, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useAssistants, useDeleteAssistant } from "@/lib/hooks/useAssistants"
import { AssistantForm } from "@/components/assistants/AssistantForm"
import type { AssistantRead } from "@/lib/types"

export default function AssistantsPage() {
  const { data: assistants, isLoading } = useAssistants()
  const deleteAssistant = useDeleteAssistant()
  const [formOpen, setFormOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<AssistantRead | undefined>(undefined)

  async function handleDelete(id: string) {
    try {
      await deleteAssistant.mutateAsync(id)
      toast.success("Assistant excluído")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao excluir")
    }
  }

  function openCreate() {
    setEditTarget(undefined)
    setFormOpen(true)
  }

  function openEdit(a: AssistantRead) {
    setEditTarget(a)
    setFormOpen(true)
  }

  return (
    <div className="p-8 max-w-2xl">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-border/60">
        <h1 className="text-lg font-semibold">Assistants</h1>
        <Button
          onClick={openCreate}
          size="sm"
          style={{ backgroundColor: "#136ddd" }}
          className="text-white"
        >
          <Plus size={13} className="mr-1.5" />
          Novo assistant
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      ) : assistants?.length === 0 ? (
        <button
          onClick={openCreate}
          className="w-full border border-dashed border-border/50 rounded-lg p-12 text-center hover:border-[#136ddd]/40 hover:bg-[#136ddd]/5 transition-colors"
        >
          <p className="text-sm text-muted-foreground">Nenhum assistant ainda.</p>
          <p className="text-xs text-muted-foreground/50 mt-1">Clique para criar o primeiro.</p>
        </button>
      ) : (
        <div className="space-y-2">
          {assistants?.map((a) => (
            <div
              key={a.assistant_id}
              className="flex items-center justify-between px-4 py-3 bg-card border border-border/60 rounded-lg"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{a.name}</p>
                {(a.context as { model?: string })?.model && (
                  <p className="font-mono text-[11px] text-muted-foreground mt-0.5">
                    {(a.context as { model?: string }).model}
                  </p>
                )}
                {a.description && (
                  <p className="text-xs text-muted-foreground/60 mt-0.5 truncate">
                    {a.description}
                  </p>
                )}
              </div>
              <div className="flex gap-1.5 shrink-0 ml-3">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-foreground"
                  onClick={() => openEdit(a)}
                >
                  <Pencil size={13} />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  onClick={() => handleDelete(a.assistant_id)}
                >
                  <Trash2 size={13} />
                </Button>
              </div>
            </div>
          ))}
          <button
            onClick={openCreate}
            className="w-full flex items-center gap-2 px-4 py-3 border border-dashed border-border/40 rounded-lg hover:border-[#136ddd]/40 hover:bg-[#136ddd]/5 transition-colors"
          >
            <Plus size={13} className="text-muted-foreground/40" />
            <span className="text-xs text-muted-foreground/40">Novo assistant</span>
          </button>
        </div>
      )}

      <AssistantForm open={formOpen} onClose={() => setFormOpen(false)} assistant={editTarget} />
    </div>
  )
}
