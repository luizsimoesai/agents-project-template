"use client"

import { useEffect, useRef } from "react"
import { useStream } from "@langchain/langgraph-sdk/react"
import { toast } from "sonner"
import { ChatMessage } from "./ChatMessage"
import { ChatInput } from "./ChatInput"
import { useAuthStore } from "@/lib/store/auth"
import type { Message } from "@langchain/langgraph-sdk"
import type { AssistantRead } from "@/lib/types"

interface ChatViewProps {
  threadId: string
  assistant: AssistantRead
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

export function ChatView({ threadId, assistant }: ChatViewProps) {
  const accessToken = useAuthStore((s) => s.accessToken)
  const bottomRef = useRef<HTMLDivElement>(null)
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:2024"

  const { messages, submit, isLoading: isStreaming, stop } = useStream<{
    messages: Array<{ role: string; content: string }>
  }>({
    apiUrl,
    assistantId: assistant.assistant_id,
    threadId,
    defaultHeaders: accessToken
      ? { Authorization: `Bearer ${accessToken}` }
      : {},
    messagesKey: "messages",
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : "Connection lost"
      toast.error("Streaming error: " + message)
    },
  })

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  function handleSubmit(content: string) {
    submit({ messages: [{ role: "human", content }] })
  }

  const displayMessages: Array<{ role: string; content: string }> = (messages ?? []).map(
    (m) => ({
      role: getMessageRole(m),
      content: getMessageContent(m),
    })
  )

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto divide-y divide-border/60">
        {displayMessages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground px-6 py-4">
            <p className="font-mono text-sm">start the conversation below</p>
          </div>
        ) : (
          displayMessages.map((msg, i) => (
            <ChatMessage
              key={i}
              role={msg.role}
              content={msg.content}
              isStreaming={
                isStreaming &&
                i === displayMessages.length - 1 &&
                (msg.role === "ai" || msg.role === "assistant")
              }
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput
        onSubmit={handleSubmit}
        onStop={stop}
        isStreaming={isStreaming}
      />
    </div>
  )
}
