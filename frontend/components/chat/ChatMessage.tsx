import { cn } from "@/lib/utils"

interface ChatMessageProps {
  role: string
  content: string
  isStreaming?: boolean
}

export function ChatMessage({ role, content, isStreaming = false }: ChatMessageProps) {
  const isAI = role === "ai" || role === "assistant"

  return (
    <div className={cn("group py-5 px-6", isAI ? "bg-transparent" : "")}>
      <div className="flex items-center gap-2 mb-2.5">
        <div
          className={cn(
            "w-1.5 h-1.5 rounded-full shrink-0",
            isAI ? "bg-[#136ddd]" : "bg-muted-foreground/50"
          )}
        />
        <span
          className={cn(
            "font-mono text-[10px] uppercase tracking-[0.18em] font-medium",
            isAI ? "text-[#136ddd]" : "text-muted-foreground"
          )}
        >
          {isAI ? "assistant" : "you"}
        </span>
      </div>
      <div
        className={cn(
          "pl-4.5 text-sm leading-7 whitespace-pre-wrap",
          isAI ? "text-foreground" : "text-foreground/75"
        )}
      >
        {content}
        {isStreaming && (
          <span
            data-testid="streaming-cursor"
            className="inline-block w-0.5 h-3.75 bg-[#136ddd] ml-0.5 align-middle"
            style={{ animation: "blink 1s steps(1) infinite" }}
          />
        )}
      </div>
    </div>
  )
}
