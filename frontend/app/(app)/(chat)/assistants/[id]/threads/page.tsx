"use client"

import type { Route } from "next"
import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { useCreateThread } from "@/lib/hooks/useThreads"
import { useModels } from "@/lib/hooks/useModels"
import { useAuthStore } from "@/lib/store/auth"
import { ChatInput } from "@/components/chat/ChatInput"
import { ModelPicker } from "@/components/chat/ModelPicker"

function greeting(name: string | null | undefined): string {
  const hour = new Date().getHours()
  const salutation = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening"
  return name ? `${salutation}, ${name.split(" ")[0]}` : salutation
}

export default function ThreadsListPage() {
  const router = useRouter()
  const { id: assistantId } = useParams<{ id: string }>()
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
    // typedRoutes: this href is built at runtime, so cast to Route.
    router.replace((url.pathname + url.search) as Route)
  }

  return (
    <div className="flex flex-col h-full items-center justify-center px-6">
      <div className="w-full max-w-2xl flex flex-col gap-8">
        <h1 className="text-xl font-medium text-foreground/80 text-center">
          {greeting(user?.name)}
        </h1>
        {models && models.length > 0 && selectedModelId && (
          <div className="flex justify-center">
            <ModelPicker
              models={models}
              value={selectedModelId}
              onChange={(id) => handleModelChange(id)}
            />
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
