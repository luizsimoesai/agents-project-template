"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { useCreateThread } from "@/lib/hooks/useThreads"
import { useModels } from "@/lib/hooks/useModels"
import { useAuthStore } from "@/lib/store/auth"
import { ChatInput } from "@/components/chat/ChatInput"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

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
  const { data: models } = useModels()
  const [selectedModelId, setSelectedModelId] = useState("")

  useEffect(() => {
    if (!models?.length || selectedModelId) return
    const defaultId = models.find((m) => m.is_default)?.model_id
    setSelectedModelId(defaultId ?? models[0]?.model_id ?? "")
  }, [models])

  const selectedModel = models?.find((m) => m.model_id === selectedModelId)

  function handleModelChange(modelId: string | null) {
    if (modelId) setSelectedModelId(modelId)
  }

  async function handleSubmit(message: string) {
    const name = message.slice(0, 50).trim()
    const t = await createThread.mutateAsync({
      assistant_id: assistantId,
      thread_name: name,
      ...(selectedModelId ? { thread_model: selectedModelId, thread_model_base_url: selectedModel?.base_url ?? null } : {}),
    })
    const url = new URL(`/assistants/${assistantId}/threads/${t.thread_id}`, window.location.origin)
    url.searchParams.set("msg", message)
    if (selectedModelId) url.searchParams.set("model", selectedModelId)
    if (selectedModel?.base_url) url.searchParams.set("model_base_url", selectedModel.base_url)
    router.replace(url.pathname + url.search)
  }

  return (
    <div className="flex flex-col h-full items-center justify-center px-6">
      <div className="w-full max-w-2xl flex flex-col gap-4">
        <h1 className="text-xl font-medium text-foreground/80 text-center">
          {greeting(user?.name)}
        </h1>
        {models && models.length > 0 && selectedModelId && (
          <div className="flex justify-center">
            <Select value={selectedModelId} onValueChange={handleModelChange}>
              <SelectTrigger className="h-7 text-xs font-mono border-border/60 bg-transparent w-auto p-0 pr-2 gap-0 overflow-hidden">
                <span className="px-2.5 h-full flex items-center bg-muted/60 border-r border-border/60 text-muted-foreground shrink-0">
                  Model
                </span>
                <SelectValue placeholder="select model..." className="px-2" />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.model_id} value={m.model_id} className="font-mono text-xs">
                    {m.model_id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
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
