"use client"

import { useRef, useState } from "react"
import { Square } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

interface ChatInputProps {
  onSubmit: (message: string) => void
  onStop: () => void
  isStreaming: boolean
  disabled?: boolean
}

export function ChatInput({ onSubmit, onStop, isStreaming, disabled }: ChatInputProps) {
  const [value, setValue] = useState("")
  const ref = useRef<HTMLTextAreaElement>(null)

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
    <div className="border-t border-border p-3 flex gap-2 items-end">
      <Textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Digite uma mensagem... (Enter para enviar, Shift+Enter para nova linha)"
        disabled={disabled || isStreaming}
        className={cn("resize-none min-h-[40px] max-h-[160px] font-mono text-sm", "flex-1")}
        rows={1}
      />
      {isStreaming ? (
        <Button
          variant="outline"
          size="icon"
          onClick={onStop}
          className="h-10 w-10 flex-shrink-0 border-destructive text-destructive hover:bg-destructive/10"
        >
          <Square size={14} />
        </Button>
      ) : (
        <Button
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          className="h-10 flex-shrink-0"
          style={{ backgroundColor: "#136ddd" }}
        >
          enviar
        </Button>
      )}
    </div>
  )
}
