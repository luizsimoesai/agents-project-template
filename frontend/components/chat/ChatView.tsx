"use client"

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { useStream } from "@langchain/langgraph-sdk/react"
import { toast } from "sonner"
import { ChatMessage } from "./ChatMessage"
import { ChatInput } from "./ChatInput"
import { useAuthStore } from "@/lib/store/auth"
import { API_URL } from "@/lib/api/client"
import { useThreadState, useUpdateThreadName, useThread } from "@/lib/hooks/useThreads"
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

// Build RenderedToolCall list from historic messages (AIMessage + ToolMessages pairing)
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
      result: toolMsg ? (typeof toolMsg.content === "string" ? toolMsg.content : JSON.stringify(toolMsg.content)) : undefined,
    } satisfies RenderedToolCall
  })
}

export function ChatView({ threadId, assistant, initialMessage, initialModel, initialModelBaseUrl }: ChatViewProps) {
  const accessToken = useAuthStore((s) => s.accessToken)
  const bottomRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const initialMessageSent = useRef(false)
  const threadNameSet = useRef(false)
  const updateThreadName = useUpdateThreadName()

  const { data: historicMessages } = useThreadState(threadId)
  const { data: thread } = useThread(threadId)
  // Model for this thread: prefer saved metadata, fall back to initialModel from URL
  const threadModel = (thread?.metadata?.thread_model as string | undefined) || initialModel || undefined
  const threadModelBaseUrl = (thread?.metadata?.thread_model_base_url as string | null | undefined) ?? null
  const modelLabel = threadModel

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
    submit(
      { messages: [{ role: "human", content: initialMessage }] },
      initialModel
        ? { config: { configurable: { model: initialModel, model_base_url: initialModelBaseUrl ?? null } } }
        : undefined
    )
    router.replace(window.location.pathname, { scroll: false })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // After the first AI response lands, name the thread from the first human message
  useEffect(() => {
    if (isStreaming || threadNameSet.current) return
    const msgs = streamMessages.length > 0 ? streamMessages : (historicMessages ?? []) as Message[]
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
      threadModel
        ? { config: { configurable: { model: threadModel, model_base_url: threadModelBaseUrl } } }
        : undefined
    )
  }

  const streamMessages = messages ?? []
  const historic = (historicMessages ?? []) as Message[]
  const usingStream = streamMessages.length > 0

  // Build display items: skip tool messages (shown inline with their AI message)
  type DisplayItem = { role: string; content: string; toolCalls: RenderedToolCall[]; isLast: boolean }

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
          modelLabel={modelLabel}
        />
    </div>
  )
}
