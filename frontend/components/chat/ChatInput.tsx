"use client"

import { useRef, useState, useEffect } from "react"
import { Square, ArrowUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

interface ChatInputProps {
  onSubmit: (message: string) => void
  onStop: () => void
  isStreaming: boolean
  disabled?: boolean
  centered?: boolean
}

export function ChatInput({ onSubmit, onStop, isStreaming, disabled, centered }: ChatInputProps) {
  const [value, setValue] = useState("")
  const ref = useRef<HTMLTextAreaElement>(null)

  // Auto-focus on mount
  useEffect(() => {
    ref.current?.focus()
  }, [])

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleSend() {
    const msg = value.trim()
    if (!msg || isStreaming) return
    onSubmit(msg)
    setValue("")
    ref.current?.focus()
  }

  return (
    <div className={centered ? "w-full" : "border-t border-border/60 px-4 py-3"}>
      <div className="relative flex items-end gap-2 bg-card border border-border rounded-xl px-3 py-2 shadow-sm focus-within:border-[#2a9d8f]/50 focus-within:ring-2 focus-within:ring-[#2a9d8f]/10 transition-all">
        <Textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message... (Enter to send)"
          disabled={disabled || isStreaming}
          className={cn(
            "resize-none min-h-9 max-h-40 font-mono text-sm flex-1",
            "border-0 shadow-none p-0 focus-visible:ring-0 bg-transparent"
          )}
          rows={1}
        />
        {isStreaming ? (
          <Button
            variant="ghost"
            size="icon"
            onClick={onStop}
            className="h-8 w-8 shrink-0 rounded-lg border border-destructive/40 text-destructive hover:bg-destructive/10"
          >
            <Square size={12} />
          </Button>
        ) : (
          <Button
            onClick={handleSend}
            disabled={!value.trim() || disabled}
            size="icon"
            className="h-8 w-8 shrink-0 rounded-lg"
            style={{ backgroundColor: value.trim() ? "#2a9d8f" : undefined }}
          >
            <ArrowUp size={14} />
          </Button>
        )}
      </div>
      <p className="text-center font-mono text-[10px] text-muted-foreground/50 mt-2 tracking-wide">
        shift+enter for new line
      </p>
    </div>
  )
}
