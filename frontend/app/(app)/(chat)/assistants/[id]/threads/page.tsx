"use client"

import { useRouter, useParams } from "next/navigation"
import { useCreateThread } from "@/lib/hooks/useThreads"
import { useAuthStore } from "@/lib/store/auth"
import { ChatInput } from "@/components/chat/ChatInput"

function greeting(name: string | null | undefined): string {
  const hour = new Date().getHours()
  const salutation = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening"
  return name ? `${salutation}, ${name.split(" ")[0]}` : salutation
}

export default function ThreadsListPage() {
  const router = useRouter()
  const params = useParams()
  const assistantId = params.id as string
  const createThread = useCreateThread()
  const user = useAuthStore((s) => s.user)

  async function handleSubmit(message: string) {
    const name = message.slice(0, 50).trim()
    const t = await createThread.mutateAsync({ assistant_id: assistantId, thread_name: name })
    router.replace(
      `/assistants/${assistantId}/threads/${t.thread_id}?msg=${encodeURIComponent(message)}`
    )
  }

  return (
    <div className="flex flex-col h-full items-center justify-center px-6">
      <div className="w-full max-w-2xl flex flex-col gap-6">
        <h1 className="text-xl font-medium text-foreground/80 text-center">
          {greeting(user?.name)}
        </h1>
        <ChatInput
          onSubmit={handleSubmit}
          onStop={() => {}}
          isStreaming={createThread.isPending}
          disabled={createThread.isPending}
          centered
        />
      </div>
    </div>
  )
}
