import { useState } from "react"
import { Loader2, CheckCircle2, XCircle, ChevronDown, ChevronRight, Wrench } from "lucide-react"
import { cn } from "@/lib/utils"

export interface RenderedToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  state: "pending" | "completed" | "error"
  result?: string
}

function tryParseJson(value: unknown): unknown {
  if (typeof value !== "string") return value
  try { return JSON.parse(value) } catch { return value }
}

function formatArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args)
  if (entries.length === 0) return ""
  return entries
    .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(", ")
}

export function ToolCallBadge({ tc }: { tc: RenderedToolCall }) {
  const [open, setOpen] = useState(false)
  const result = tryParseJson(tc.result)
  const hasContent = tc.result != null

  return (
    <div
      className={cn(
        "inline-flex flex-col rounded-md border text-xs font-mono mb-1 max-w-full",
        tc.state === "error"
          ? "border-destructive/40 bg-destructive/5"
          : "border-border/60 bg-muted/30"
      )}
    >
      {/* Header row */}
      <button
        type="button"
        onClick={() => hasContent && setOpen((o) => !o)}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 text-left",
          hasContent ? "cursor-pointer hover:bg-white/5" : "cursor-default"
        )}
      >
        {/* State icon */}
        {tc.state === "pending" && (
          <Loader2 size={12} className="shrink-0 text-[#2a9d8f] animate-spin" />
        )}
        {tc.state === "completed" && (
          <CheckCircle2 size={12} className="shrink-0 text-[#2a9d8f]" />
        )}
        {tc.state === "error" && (
          <XCircle size={12} className="shrink-0 text-destructive" />
        )}

        <Wrench size={11} className="shrink-0 text-foreground/40" />

        {/* Tool name */}
        <span className={cn(
          "font-semibold tracking-wide",
          tc.state === "error" ? "text-destructive" : "text-foreground/80"
        )}>
          {tc.name}
        </span>

        {/* Args summary */}
        {Object.keys(tc.args).length > 0 && (
          <span className="text-foreground/40 truncate max-w-[220px]">
            {formatArgs(tc.args)}
          </span>
        )}

        {/* Expand chevron */}
        {hasContent && (
          <span className="ml-auto shrink-0 text-foreground/40">
            {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
          </span>
        )}
      </button>

      {/* Expanded result */}
      {open && hasContent && (
        <div className="px-3 pb-2 border-t border-border/40 pt-2">
          <pre className="text-[11px] text-foreground/70 whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
            {typeof result === "string"
              ? result
              : JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
