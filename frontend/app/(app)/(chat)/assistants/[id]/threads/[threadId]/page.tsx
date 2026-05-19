"use client"

import { useParams, useSearchParams } from "next/navigation"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { ChatView } from "@/components/chat/ChatView"
import { Skeleton } from "@/components/ui/skeleton"

export default function ChatPage() {
  const { id: assistantId, threadId } = useParams<{
    id: string
    threadId: string
  }>()
  const searchParams = useSearchParams()
  const initialMessage = searchParams.get("msg") ?? undefined
  const initialModel = searchParams.get("model") ?? undefined
  const initialModelBaseUrl = searchParams.get("model_base_url") ?? undefined

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
        <p className="font-mono text-sm text-muted-foreground">assistant not found</p>
      </div>
    )
  }

  return <ChatView threadId={threadId} assistant={assistant} initialMessage={initialMessage} initialModel={initialModel} initialModelBaseUrl={initialModelBaseUrl} />
}
