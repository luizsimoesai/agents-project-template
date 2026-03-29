import { cn } from "@/lib/utils"
import { Separator } from "@/components/ui/separator"

interface ChatMessageProps {
  role: string
  content: string
  isStreaming?: boolean
}

export function ChatMessage({ role, content, isStreaming = false }: ChatMessageProps) {
  const isAI = role === "ai" || role === "assistant"

  return (
    <div className="py-3">
      <div className="mb-1.5 flex items-center gap-2">
        <span
          className="font-mono text-[11px] uppercase tracking-widest font-semibold"
          style={{ color: isAI ? "#136ddd" : undefined }}
        >
          {isAI ? "assistant" : "você"}
        </span>
      </div>
      <p className="text-sm leading-relaxed whitespace-pre-wrap">
        {content}
        {isStreaming && (
          <span
            data-testid="streaming-cursor"
            className={cn(
              "inline-block w-[5px] h-[14px] bg-[#136ddd] rounded-sm ml-0.5 align-middle",
              "animate-pulse"
            )}
          />
        )}
      </p>
      <Separator className="mt-3" />
    </div>
  )
}
