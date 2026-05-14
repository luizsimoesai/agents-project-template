# Frontend Design Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish three visual areas of the frontend — assistant card badge, new-thread model select, and chat model info display.

**Architecture:** Three independent file-level changes. Tasks 1 and 2 each touch a single file. Task 3 touches two files (`ChatInput.tsx` and `ChatView.tsx`) that must be updated together because a new prop flows from ChatView into ChatInput.

**Tech Stack:** Next.js 16, React 19, Tailwind CSS v4, Base UI (shadcn/ui wrappers in `components/ui/`), TypeScript. Run `npm run build` from `frontend/` to type-check.

---

## File Map

| File | Change |
|------|--------|
| `frontend/app/(app)/(picker)/assistants/page.tsx` | Remove badge background/padding, apply accent text color |
| `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx` | Restructure SelectTrigger with "Model" prefix; show `model_id` in trigger and items |
| `frontend/components/chat/ChatInput.tsx` | Add `modelLabel?: string` prop; render model header inside the rounded input box |
| `frontend/components/chat/ChatView.tsx` | Remove outer `border-t` wrapper; pass `modelLabel` (raw `model_id`) to ChatInput |

---

## Task 1: Assistant Card Badge — Remove Background

**Files:**
- Modify: `frontend/app/(app)/(picker)/assistants/page.tsx:127`

- [ ] **Step 1: Replace badge classes**

Find line 127 in `frontend/app/(app)/(picker)/assistants/page.tsx`:

```tsx
// BEFORE
<span className="inline-block mt-2 px-2 py-0.5 rounded text-xs bg-accent text-muted-foreground">
  {getGraphType(a.graph_id)?.label ?? a.graph_id}
</span>
```

Replace with:

```tsx
// AFTER
<span className="inline-block mt-2 text-[11px] text-accent font-medium">
  {getGraphType(a.graph_id)?.label ?? a.graph_id}
</span>
```

Changes: remove `px-2 py-0.5 rounded bg-accent text-muted-foreground text-xs`; add `text-[11px] text-accent font-medium`.

- [ ] **Step 2: Type-check**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors. Build warnings about image optimisation are fine; errors about `text-accent` are not — `text-accent` is a valid Tailwind v4 CSS variable token.

- [ ] **Step 3: Visual check**

Start the dev server (`npm run dev` from `frontend/`) and open `http://localhost:3000`. Navigate to the assistants picker screen. The graph type label should now appear as unstyled amber text without any background pill, at a slightly smaller size than the assistant name.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(app\)/\(picker\)/assistants/page.tsx
git commit -m "style: remove background from assistant card graph-type badge"
```

---

## Task 2: New-Thread Model Select — Split-Button Layout + model_id

**Files:**
- Modify: `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx:64–79`

### Background

`SelectTrigger` (defined in `frontend/components/ui/select.tsx`) renders as a flex container with `justify-between` and appends a `ChevronDownIcon` as its last child. Its default classes include `px-3 py-2 gap-2`. Overriding these with `p-0 pr-2 gap-0` in `className` (merged via `cn`/tailwind-merge) gives us full control over the internal layout.

`SelectValue` (same file) has `flex-1 text-left truncate` as defaults, so it naturally fills the space between the "Model" prefix and the chevron.

- [ ] **Step 1: Restructure the Select block**

In `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx`, find the `<div className="flex justify-center">` block (lines 64–79) and replace it entirely:

```tsx
// BEFORE (lines 64–79)
{models && models.length > 0 && selectedModelId && (
  <div className="flex justify-center">
    <Select value={selectedModelId} onValueChange={handleModelChange}>
      <SelectTrigger className="h-7 text-xs font-mono border-border/60 bg-transparent w-auto min-w-45">
        <SelectValue placeholder="select model..." />
      </SelectTrigger>
      <SelectContent>
        {models.map((m) => (
          <SelectItem key={m.model_id} value={m.model_id} className="font-mono text-xs">
            {m.display_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
)}
```

```tsx
// AFTER
{models && models.length > 0 && selectedModelId && (
  <div className="flex justify-center">
    <Select value={selectedModelId} onValueChange={handleModelChange}>
      <SelectTrigger className="h-7 text-xs font-mono border-border/60 bg-transparent w-auto p-0 pr-2 gap-0 overflow-hidden">
        <span className="px-2.5 h-full flex items-center bg-muted/60 border-r border-border/60 text-muted-foreground shrink-0">
          Model
        </span>
        <SelectValue placeholder="select model..." className="px-2" />
      </SelectTrigger>
      <SelectContent>
        {models.map((m) => (
          <SelectItem key={m.model_id} value={m.model_id} className="font-mono text-xs">
            {m.model_id}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
)}
```

Key changes:
- `SelectTrigger`: `p-0 pr-2 gap-0 overflow-hidden` (override default padding/gap; clip the prefix background at corners)
- Added `<span>` prefix "Model" with `bg-muted/60 border-r border-border/60`
- `SelectValue` gets `className="px-2"` for horizontal padding
- `SelectItem` children: `{m.model_id}` instead of `{m.display_name}`

- [ ] **Step 2: Type-check**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors. The `<span>` inside `SelectTrigger` is valid because `SelectTrigger` renders `{children}` directly.

- [ ] **Step 3: Visual check**

On `http://localhost:3000`, navigate to an assistant and open the new-thread screen. The select should show a "Model |" prefix (slightly tinted background, right border) followed by the selected model ID. Opening the dropdown should list model IDs (e.g. `anthropic/claude-sonnet-4-6`). The trigger width should remain stable when switching between models.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(app\)/\(chat\)/assistants/\[id\]/threads/page.tsx
git commit -m "style: add Model prefix to thread select trigger; show model_id"
```

---

## Task 3: Chat Model Info — Integrate into Input Box

**Files:**
- Modify: `frontend/components/chat/ChatInput.tsx`
- Modify: `frontend/components/chat/ChatView.tsx`

These two files must be updated together: `ChatView` passes the new `modelLabel` prop, and `ChatInput` consumes it.

### Background

`ChatInput` currently adds `border-t border-border/60` as the outer wrapper when `centered` is false (line 42). `ChatView` wraps `ChatInput` in an additional `border-t` div and renders the model label above it — producing two stacked horizontal lines. The fix removes `ChatView`'s wrapper and places the model header inside the `rounded-xl` input box in `ChatInput`.

- [ ] **Step 1: Update ChatInputProps and render the model header**

Replace the entire contents of `frontend/components/chat/ChatInput.tsx`:

```tsx
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
  modelLabel?: string
}

export function ChatInput({ onSubmit, onStop, isStreaming, disabled, centered, modelLabel }: ChatInputProps) {
  const [value, setValue] = useState("")
  const ref = useRef<HTMLTextAreaElement>(null)

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
      <div className="bg-card border border-border rounded-xl shadow-sm focus-within:border-[#2a9d8f]/50 focus-within:ring-2 focus-within:ring-[#2a9d8f]/10 transition-all overflow-hidden">
        {modelLabel && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 border-b border-border/40 bg-muted/20">
            <div className="w-1.5 h-1.5 rounded-full bg-[#2a9d8f] shrink-0" />
            <span className="text-[10px] font-mono text-muted-foreground/60">model</span>
            <span className="text-[10px] font-mono text-muted-foreground font-medium">{modelLabel}</span>
          </div>
        )}
        <div className="relative flex items-end gap-2 px-3 py-2">
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
      </div>
      <p className="text-center font-mono text-[10px] text-muted-foreground/50 mt-2 tracking-wide">
        shift+enter for new line
      </p>
    </div>
  )
}
```

Key changes from the original:
- Added `modelLabel?: string` to `ChatInputProps`
- The `rounded-xl` div lost `relative flex items-end gap-2 px-3 py-2` — replaced with `overflow-hidden` only
- Inside it, an optional model header (`border-b bg-muted/20`) renders when `modelLabel` is set
- A new inner `div` (`relative flex items-end gap-2 px-3 py-2`) holds the textarea and buttons (same layout as before)

- [ ] **Step 2: Update ChatView to pass modelLabel and remove the wrapper**

In `frontend/components/chat/ChatView.tsx`, make two changes:

**2a.** On the line that defines `modelLabel` (line 79), change it to use `threadModel` directly:

```tsx
// BEFORE (line 79)
const modelLabel = models?.find((m) => m.model_id === threadModel)?.display_name ?? threadModel

// AFTER
const modelLabel = threadModel
```

This makes the chat view show the same `model_id` string as the new-thread select, and removes the dependency on `models` data for the label.

**2b.** Replace the bottom section (lines 188–200):

```tsx
// BEFORE (lines 188–200)
      <div className="border-t border-border/60">
        {modelLabel && (
          <div className="px-4 pt-2 flex items-center gap-1.5">
            <span className="text-[10px] font-mono text-muted-foreground/50">model</span>
            <span className="text-[10px] font-mono text-muted-foreground">{modelLabel}</span>
          </div>
        )}
        <ChatInput
          onSubmit={handleSubmit}
          onStop={stop}
          isStreaming={isStreaming}
        />
      </div>
```

```tsx
// AFTER
        <ChatInput
          onSubmit={handleSubmit}
          onStop={stop}
          isStreaming={isStreaming}
          modelLabel={modelLabel}
        />
```

`ChatInput` already adds `border-t border-border/60` in non-centered mode, so removing the wrapper div does not lose the visual separator between messages and input.

Note: the `models` import and `useModels` hook can be removed from `ChatView.tsx` since `modelLabel` no longer needs them. Check for other usages before removing — if `models` is used nowhere else in the file, delete the import and the hook call.

- [ ] **Step 3: Remove unused imports from ChatView if applicable**

After step 2, check if `useModels` and `models` are used anywhere else in `ChatView.tsx`:

```bash
grep -n "models\|useModels" frontend/components/chat/ChatView.tsx
```

If the only remaining references are the hook call and `modelLabel` line (which you've already changed), remove them:
- Delete the `import { useModels } from "@/lib/hooks/useModels"` line
- Delete the `const { data: models } = useModels()` line

- [ ] **Step 4: Type-check**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors. The new `modelLabel` prop is `string | undefined`, matching `ChatInputProps`.

- [ ] **Step 5: Visual check**

On `http://localhost:3000`, open an existing thread. The input area should show a small header inside the rounded box with a green dot, `model`, and the model ID (e.g. `anthropic/claude-sonnet-4-6`). Only one border should appear between the messages list and the input — no stacked borders. The `shift+enter for new line` hint should still appear below the input box.

Also verify the new-thread screen (before any message is sent): `ChatInput` there uses `centered={true}`, so `modelLabel` is never passed and the header should not appear.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/chat/ChatInput.tsx frontend/components/chat/ChatView.tsx
git commit -m "style: move model label inside chat input box; remove duplicate border"
```
