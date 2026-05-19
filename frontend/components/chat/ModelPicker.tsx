"use client"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { ModelRead } from "@/lib/types"
import { cn } from "@/lib/utils"

interface ModelPickerProps {
  models: ModelRead[]
  value: string
  onChange: (modelId: string) => void
  // `compact` switches to the inline-in-ChatInput variant (smaller, no border chrome).
  compact?: boolean
  disabled?: boolean
}

export function ModelPicker({ models, value, onChange, compact, disabled }: ModelPickerProps) {
  if (!models.length) return null

  return (
    <Select value={value} onValueChange={(v: string) => onChange(v)} disabled={disabled}>
      <SelectTrigger
        className={cn(
          "font-mono text-xs bg-transparent w-auto p-0 gap-0 overflow-hidden transition-colors",
          compact
            ? "h-6 border-0 hover:bg-muted/30 px-2"
            : "h-7 border-[#2a9d8f]/50 pr-2 hover:border-[#2a9d8f]/80"
        )}
        aria-label={`Model: ${value || "none"}`}
      >
        {!compact && (
          <span className="px-2.5 h-full flex items-center bg-[#2a9d8f]/10 border-r border-[#2a9d8f]/30 text-[#2a9d8f]/80 shrink-0">
            Model
          </span>
        )}
        {compact && <div className="w-1.5 h-1.5 rounded-full bg-[#2a9d8f] shrink-0 mr-1.5" />}
        <SelectValue placeholder="select model..." className={compact ? "min-w-0" : "px-2 min-w-0"} />
      </SelectTrigger>
      <SelectContent>
        {models.map((m) => (
          <SelectItem key={m.model_id} value={m.model_id} className="font-mono text-xs">
            {m.model_id}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
