"use client"

import { useParams } from "next/navigation"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { ChatView } from "@/components/chat/ChatView"
import { Skeleton } from "@/components/ui/skeleton"

export default function ChatPage() {
  const params = useParams()
  const assistantId = params.id as string
  const threadId = params.threadId as string

  const { data: assistants, isLoading } = useAssistants()
  const assistant = assistants?.find((a) => a.assistant_id === assistantId)

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-64" />
      </div>
    )
  }

  if (!assistant) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="font-mono text-sm text-muted-foreground">assistente não encontrado</p>
      </div>
    )
  }

  return <ChatView threadId={threadId} assistant={assistant} />
}
