"use client"

import { useParams } from "next/navigation"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Pencil } from "lucide-react"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { AssistantForm } from "@/components/assistants/AssistantForm"
import { Skeleton } from "@/components/ui/skeleton"

export default function AssistantDetailPage() {
  const params = useParams()
  const id = params.id as string
  const { data: assistants, isLoading } = useAssistants()
  const assistant = assistants?.find((a) => a.assistant_id === id)
  const [editOpen, setEditOpen] = useState(false)

  if (isLoading) return <div className="p-6"><Skeleton className="h-8 w-48" /></div>
  if (!assistant) return <div className="p-6 font-mono text-sm text-muted-foreground">assistente não encontrado</div>

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-mono font-semibold" style={{ color: "#136ddd" }}>
          {assistant.name}
        </h2>
        <Button variant="ghost" size="icon" onClick={() => setEditOpen(true)}>
          <Pencil size={14} />
        </Button>
      </div>
      {assistant.description && (
        <p className="text-sm text-muted-foreground">{assistant.description}</p>
      )}
      {(assistant.context as { model?: string })?.model && (
        <p className="font-mono text-xs text-muted-foreground">
          model: {(assistant.context as { model?: string }).model}
        </p>
      )}
      <AssistantForm open={editOpen} onClose={() => setEditOpen(false)} assistant={assistant} />
    </div>
  )
}
