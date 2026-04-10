"use client"

import { cn } from "@/lib/utils"
import { DollarSign, Zap } from "lucide-react"

export interface BudgetUpdate {
  tokens_input: number
  tokens_output: number
  tokens_total: number
  token_limit: number | null
  cost_limit: number | null
  cost_usd: number | null
  token_percent: number | null
  cost_percent: number | null
  context_window_tokens: number
  context_window_size: number | null
  context_window_percent: number | null
  warning_triggered: boolean
  limit_reached: boolean
}

interface BudgetWidgetProps {
  data: BudgetUpdate
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function formatCost(n: number): string {
  if (n < 0.0001) return `<$0.0001`
  if (n < 0.01) return `$${n.toFixed(4)}`
  return `$${n.toFixed(3)}`
}

function MiniBar({
  pct,
  color,
  width = "w-14",
}: {
  pct: number
  color: string
  width?: string
}) {
  return (
    <div className={cn("h-0.75 rounded-full bg-muted/50 overflow-hidden shrink-0", width)}>
      <div
        className={cn("h-full rounded-full transition-all duration-500", color)}
        style={{ width: `${Math.min(pct * 100, 100)}%` }}
      />
    </div>
  )
}

export function BudgetWidget({ data }: BudgetWidgetProps) {
  const isWarning = data.warning_triggered && !data.limit_reached
  const isLimit = data.limit_reached

  // Derived flags — what is actually configured
  const hasCost = data.cost_usd !== null
  const hasTokenLimit = data.token_limit !== null
  const hasCostLimit = data.cost_limit !== null
  const hasContextWindow = data.context_window_size !== null && data.context_window_size > 0
  const hasInputOutput = data.tokens_input > 0 || data.tokens_output > 0

  // Colors by state
  const stateColor = isLimit
    ? "text-destructive"
    : isWarning
    ? "text-[#f4a261]"
    : "text-[#2a9d8f]"

  const barColor = isLimit
    ? "bg-destructive"
    : isWarning
    ? "bg-[#f4a261]"
    : "bg-[#2a9d8f]"

  const contextBarColor =
    (data.context_window_percent ?? 0) > 0.85
      ? "bg-destructive"
      : (data.context_window_percent ?? 0) > 0.65
      ? "bg-[#f4a261]"
      : "bg-muted-foreground/40"

  const border = isLimit
    ? "border-destructive/30"
    : isWarning
    ? "border-[#f4a261]/30"
    : "border-border/60"

  return (
    <div
      className={cn(
        "flex flex-col gap-1.5 rounded-xl",
        "bg-card/85 backdrop-blur-sm border",
        "px-3 py-2 text-[10.5px] font-mono",
        "transition-all duration-300",
        border
      )}
    >
      {/* ── Row 1: Tokens ─────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <Zap size={10} className={cn("shrink-0", stateColor)} />

        <span className={cn("tabular-nums", isLimit || isWarning ? stateColor : "text-foreground/65")}>
          {formatTokens(data.tokens_total)}
          {hasTokenLimit && (
            <span className="text-foreground/30">
              {" "}/{" "}{formatTokens(data.token_limit!)}
            </span>
          )}
        </span>

        {hasTokenLimit && data.token_percent !== null && (
          <MiniBar pct={data.token_percent} color={barColor} />
        )}

        {/* in / out breakdown — only when both are nonzero */}
        {hasInputOutput && (
          <span className="text-foreground/28 tabular-nums">
            ↑{formatTokens(data.tokens_input)}{" "}↓{formatTokens(data.tokens_output)}
          </span>
        )}

        {isLimit && (
          <span className="text-destructive font-semibold uppercase text-[9px] tracking-wide ml-0.5">
            limit
          </span>
        )}
      </div>

      {/* ── Row 2: Cost ───────────────────────────────────── */}
      {hasCost && (
        <div className="flex items-center gap-2">
          <DollarSign size={10} className={cn("shrink-0", isLimit || isWarning ? stateColor : "text-foreground/35")} />
          <span className={cn("tabular-nums", isLimit || isWarning ? stateColor : "text-foreground/50")}>
            {formatCost(data.cost_usd!)}
            {hasCostLimit && (
              <span className="text-foreground/28">
                {" "}/{" "}{formatCost(data.cost_limit!)}
              </span>
            )}
          </span>

          {hasCostLimit && data.cost_percent !== null && (
            <MiniBar pct={data.cost_percent} color={barColor} />
          )}
        </div>
      )}

      {/* ── Row 3: Context window ─────────────────────────── */}
      {hasContextWindow && data.context_window_percent !== null && (
        <div className="flex items-center gap-2 pl-4.5">
          <span className="text-foreground/28">
            ctx {formatTokens(data.context_window_tokens)}/{formatTokens(data.context_window_size!)}
          </span>
          <MiniBar pct={data.context_window_percent} color={contextBarColor} width="w-10" />
        </div>
      )}
    </div>
  )
}
