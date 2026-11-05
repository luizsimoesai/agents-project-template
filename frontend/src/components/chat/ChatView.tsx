"use client"

import type { Route } from "next"
import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useStream } from "@langchain/langgraph-sdk/react"
import { toast } from "sonner"
import { ChatMessage } from "./ChatMessage"
import { ChatInput } from "./ChatInput"
import { useAuthStore } from "@/lib/store/auth"
import { API_URL } from "@/lib/api/client"
import {
  useThreadState,
  useUpdateThreadName,
  useThread,
  useUpdateThreadModel,
} from "@/lib/hooks/useThreads"
import { useModels } from "@/lib/hooks/useModels"
import type { Message, AIMessage, ToolMessage } from "@langchain/langgraph-sdk"
import type { AssistantRead } from "@/lib/types"
import type { RenderedToolCall } from "./ToolCallBadge"

interface ChatViewProps {
  threadId: string
  assistant: AssistantRead
  initialMessage?: string
  initialModel?: string
  initialModelBaseUrl?: string
}

function getMessageRole(msg: Message): string {
  if (msg.type === "human") return "human"
  if (msg.type === "ai") return "ai"
  return msg.type ?? "ai"
}

function getMessageContent(msg: Message): string {
  const c = msg.content
  if (typeof c === "string") return c
  return c
    .filter((part): part is { type: "text"; text: string } => part.type === "text")
    .map((part) => part.text)
    .join("")
}

// AIMessage.additional_kwargs is loosely typed in the SDK; pull model_id safely.
function getModelId(msg: Message): string | undefined {
  const kwargs = (msg as { additional_kwargs?: Record<string, unknown> }).additional_kwargs
  const v = kwargs?.model_id
  return typeof v === "string" ? v : undefined
}

function buildHistoricToolCalls(
  aiMsg: AIMessage,
  allMessages: Message[]
): RenderedToolCall[] {
  const rawCalls = aiMsg.tool_calls ?? []
  if (rawCalls.length === 0) return []

  const toolMessages = allMessages.filter(
    (m): m is ToolMessage => m.type === "tool"
  )

  return rawCalls.map((call, i) => {
    const toolMsg = toolMessages.find((tm) => tm.tool_call_id === call.id)
    return {
      id: call.id ?? `${aiMsg.id}-${i}`,
      name: call.name,
      args: (call.args ?? {}) as Record<string, unknown>,
      state: toolMsg ? "completed" : "pending",
      result: toolMsg
        ? typeof toolMsg.content === "string"
          ? toolMsg.content
          : JSON.stringify(toolMsg.content)
        : undefined,
    } satisfies RenderedToolCall
  })
}

export function ChatView({
  threadId,
  assistant,
  initialMessage,
  initialModel,
  initialModelBaseUrl,
}: ChatViewProps) {
  const accessToken = useAuthStore((s) => s.accessToken)
  const bottomRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const initialMessageSent = useRef(false)
  const threadNameSet = useRef(false)
  const updateThreadName = useUpdateThreadName()
  const updateThreadModel = useUpdateThreadModel()

  const { data: historicMessages } = useThreadState(threadId)
  const { data: thread } = useThread(threadId)
  const { data: models } = useModels()

  // selectedModelId is the source of truth for the *next* submit().
  // Initialized from thread metadata; falls back to initialModel from URL.
  const [selectedModelId, setSelectedModelId] = useState<string>("")
  const [selectedModelBaseUrl, setSelectedModelBaseUrl] = useState<string | null>(null)
  const modelInitialized = useRef(false)

  useEffect(() => {
    if (modelInitialized.current) return
    const fromMeta = thread?.metadata?.thread_model as string | undefined
    const fromMetaBaseUrl =
      (thread?.metadata?.thread_model_base_url as string | null | undefined) ?? null
    const seed = fromMeta ?? initialModel ?? ""
    const seedBaseUrl = fromMeta ? fromMetaBaseUrl : (initialModelBaseUrl ?? null)
    if (seed) {
      setSelectedModelId(seed)
      setSelectedModelBaseUrl(seedBaseUrl)
      modelInitialized.current = true
    }
  }, [thread, initialModel, initialModelBaseUrl])

  function handleModelChange(modelId: string) {
    const previous = { id: selectedModelId, baseUrl: selectedModelBaseUrl }
    const next = models?.find((m) => m.model_id === modelId)
    const baseUrl = next?.base_url ?? null
    setSelectedModelId(modelId)
    setSelectedModelBaseUrl(baseUrl)
    updateThreadModel.mutate(
      { id: threadId, modelId, baseUrl },
      {
        onError: (err) => {
          setSelectedModelId(previous.id)
          setSelectedModelBaseUrl(previous.baseUrl)
          const detail = err instanceof Error ? err.message : "Failed to persist model"
          toast.error(detail)
        },
      }
    )
  }

  const { messages, submit, isLoading: isStreaming, stop } = useStream<{
    messages: Array<{ role: string; content: string }>
  }>({
    apiUrl: API_URL,
    assistantId: assistant.assistant_id,
    threadId,
    defaultHeaders: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    messagesKey: "messages",
    onError: (err: unknown) => {
      if (!useAuthStore.getState().accessToken) return
      const message = err instanceof Error ? err.message : "Connection lost"
      toast.error("Streaming error: " + message)
    },
  })

  // Auto-submit the first message when arriving from the "new thread" flow
  useEffect(() => {
    if (!initialMessage || initialMessageSent.current) return
    initialMessageSent.current = true
    const modelForFirst = initialModel ?? selectedModelId
    submit(
      { messages: [{ role: "human", content: initialMessage }] },
      modelForFirst
        ? {
            config: {
              configurable: {
                model: modelForFirst,
                model_base_url: initialModelBaseUrl ?? selectedModelBaseUrl ?? null,
              },
            },
          }
        : undefined
    )
    router.replace(window.location.pathname as Route, { scroll: false })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // After the first AI response lands, name the thread from the first human message
  useEffect(() => {
    if (isStreaming || threadNameSet.current) return
    const msgs =
      streamMessages.length > 0
        ? streamMessages
        : ((historicMessages ?? []) as Message[])
    const humanMsg = msgs.find((m) => getMessageRole(m) === "human")
    const aiMsg = msgs.find((m) => getMessageRole(m) === "ai" || getMessageRole(m) === "assistant")
    if (!humanMsg || !aiMsg) return
    const candidate = getMessageContent(humanMsg).slice(0, 50).trim()
    if (!candidate) return
    threadNameSet.current = true
    updateThreadName.mutate({ id: threadId, name: candidate })
  }, [isStreaming]) // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, historicMessages])

  function handleSubmit(content: string) {
    submit(
      { messages: [{ role: "human", content }] },
      selectedModelId
        ? {
            config: {
              configurable: {
                model: selectedModelId,
                model_base_url: selectedModelBaseUrl,
              },
            },
          }
        : undefined
    )
  }

  const streamMessages = messages ?? []
  const historic = (historicMessages ?? []) as Message[]
  const usingStream = streamMessages.length > 0

  type DisplayItem = {
    role: string
    content: string
    toolCalls: RenderedToolCall[]
    isLast: boolean
    modelId?: string
  }

  const displayItems: DisplayItem[] = (() => {
    const source = usingStream ? streamMessages : historic
    const visible = source.filter((m) => m.type !== "tool" && m.type !== "system")

    return visible.map((msg, i) => {
      let toolCalls: RenderedToolCall[] = []
      if (msg.type === "ai") {
        toolCalls = buildHistoricToolCalls(msg as AIMessage, source)
      }
      return {
        role: getMessageRole(msg),
        content: getMessageContent(msg),
        toolCalls,
        isLast: i === visible.length - 1,
        modelId: getModelId(msg),
      }
    })
  })()

  return (
    <div className="relative flex flex-col h-full">
      <div className="flex-1 overflow-y-auto divide-y divide-border/60">
        {displayItems.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground px-6 py-4">
            <p className="font-mono text-sm">What can I help you with today?</p>
          </div>
        ) : (
          displayItems.map((item, i) => (
            <ChatMessage
              key={i}
              role={item.role}
              content={item.content}
              toolCalls={item.toolCalls}
              modelId={item.modelId}
              isStreaming={
                isStreaming &&
                item.isLast &&
                (item.role === "ai" || item.role === "assistant")
              }
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <ChatInput
        onSubmit={handleSubmit}
        onStop={stop}
        isStreaming={isStreaming}
        models={models}
        selectedModelId={selectedModelId}
        onModelChange={handleModelChange}
      />
    </div>
  )
}
