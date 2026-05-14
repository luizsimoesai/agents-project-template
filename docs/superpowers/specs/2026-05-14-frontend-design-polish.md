# Frontend Design Polish

**Date:** 2026-05-14  
**Status:** Approved

## Overview

Three targeted visual improvements to the frontend:

1. Assistant card badge — remove orange background, use accent text only
2. New thread model select — add "Model" prefix inside trigger, show `model_id` instead of `display_name`
3. Chat model info — integrate into the input box as a header, eliminating duplicate borders

---

## 1. Assistant Card Badge

**File:** `frontend/app/(app)/(picker)/assistants/page.tsx`

### Current

```tsx
<span className="inline-block mt-2 px-2 py-0.5 rounded text-xs bg-accent text-muted-foreground">
  {getGraphType(a.graph_id)?.label ?? a.graph_id}
</span>
```

The badge has a Sandy Brown (`--accent`) background with muted text, which draws more attention than this secondary metadata deserves.

### New

```tsx
<span className="inline-block mt-2 text-[11px] text-accent font-medium">
  {getGraphType(a.graph_id)?.label ?? a.graph_id}
</span>
```

Remove all background/padding/border-radius. Use `text-accent` (Sandy Brown) at 11px with medium weight. The graph type stays visible but reads as secondary information rather than a badge.

---

## 2. New Thread Model Select

**File:** `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx`

### Current

```tsx
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
```

Problems:
- No label — the select's purpose isn't immediately obvious
- Shows `display_name` in the trigger, which varies widely in length and causes the trigger to resize when the user picks a different model

### New

The `SelectTrigger` renders a split-button style: a "Model" prefix with a right border and slightly tinted background, followed by the selected `model_id`. Both the trigger and dropdown items show `model_id`.

```tsx
<div className="flex justify-center">
  <Select value={selectedModelId} onValueChange={handleModelChange}>
    <SelectTrigger className="h-7 text-xs font-mono border-border/60 bg-transparent w-auto p-0 overflow-hidden">
      <span className="px-2.5 h-full flex items-center bg-muted/60 border-r border-border/60 text-muted-foreground shrink-0">
        Model
      </span>
      <span className="px-2.5">
        <SelectValue placeholder="select model..." />
      </span>
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
```

The trigger width stabilises because `model_id` strings are shorter and more uniform than `display_name`.

> **Note:** The `SelectTrigger` from shadcn/ui wraps content in a flex container. The prefix span and value span must be structured so the chevron icon (added by `SelectTrigger` itself) still appears at the right edge. Verify rendering and adjust padding if the Base UI implementation differs.

---

## 3. Chat Model Info

**Files:** `frontend/components/chat/ChatView.tsx`, `frontend/components/chat/ChatInput.tsx`

### Current

`ChatView` wraps the model label and `ChatInput` in a `border-t` div:

```tsx
<div className="border-t border-border/60">
  {modelLabel && (
    <div className="px-4 pt-2 flex items-center gap-1.5">
      <span className="text-[10px] font-mono text-muted-foreground/50">model</span>
      <span className="text-[10px] font-mono text-muted-foreground">{modelLabel}</span>
    </div>
  )}
  <ChatInput onSubmit={handleSubmit} onStop={stop} isStreaming={isStreaming} />
</div>
```

`ChatInput` (non-centered mode, line 42) adds its own `border-t border-border/60`, resulting in two horizontal borders stacked close together, plus the border of the input box itself — three lines total when the model label is present.

### New

**`ChatView.tsx`** — remove the wrapper div with `border-t`; pass `modelLabel` directly to `ChatInput`:

```tsx
<ChatInput
  onSubmit={handleSubmit}
  onStop={stop}
  isStreaming={isStreaming}
  modelLabel={modelLabel}
/>
```

The variable `modelLabel` currently resolves to `display_name ?? model_id`. Change it to use `model_id` directly for consistency with the select:

```tsx
const modelLabel = threadModel  // model_id string, or undefined
```

**`ChatInput.tsx`** — add `modelLabel?: string` to props; when present, render a header bar inside the `rounded-xl` input box, before the textarea:

```tsx
interface ChatInputProps {
  // ... existing props
  modelLabel?: string
}

// Inside the rounded-xl div, prepend:
{props.modelLabel && (
  <div className="flex items-center gap-1.5 px-3 py-1.5 border-b border-border/40 bg-muted/20">
    <div className="w-1.5 h-1.5 rounded-full bg-[#2a9d8f] shrink-0" />
    <span className="text-[10px] font-mono text-muted-foreground/60">model</span>
    <span className="text-[10px] font-mono text-muted-foreground font-medium">{props.modelLabel}</span>
  </div>
)}
```

The `rounded-xl` div needs `overflow-hidden` so the header's background is clipped correctly at the top corners.

### Result

One border separates the messages area from the input zone (from `ChatInput`'s own `border-t`). The model name appears as a subtle header inside the input box, visually connected to the textarea rather than floating above it.

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/app/(app)/(picker)/assistants/page.tsx` | Badge: remove bg, padding; use `text-accent text-[11px]` |
| `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx` | Select: split-button prefix "Model", show `model_id` in trigger and items |
| `frontend/components/chat/ChatView.tsx` | Remove outer `border-t` wrapper, pass `modelLabel` (model_id) to ChatInput |
| `frontend/components/chat/ChatInput.tsx` | Add `modelLabel?` prop, render header inside input box |
