# Assistant Icon Picker

**Date:** 2026-05-16
**Status:** Approved

## Overview

Allow users to choose a custom icon for each assistant they create. The selected icon is stored in `assistant.metadata.icon` and displayed on the assistant card and anywhere else the assistant is represented visually. No backend changes are required.

## Icon Set

12 icons from lucide-react (already installed), all themed around AI agents:

| Key | Label | Use case |
|---|---|---|
| `sparkles` | Sparkles | AI magic, generation |
| `brain` | Brain | Intelligence, reasoning |
| `zap` | Zap | Fast, real-time |
| `workflow` | Workflow | Pipelines, LangGraph |
| `cpu` | CPU | Compute, processing |
| `network` | Network | Multi-agent, distributed |
| `search` | Search | Research, retrieval |
| `code` | Code | Code generation |
| `database` | Database | Data agents, SQL |
| `globe` | Globe | Web agent, internet |
| `microscope` | Microscope | Deep research |
| `shield` | Shield | Security, compliance |

Default icon when none is set: `sparkles`.

## Architecture

### `lib/icon-map.ts` (new file)

Central registry following the same pattern as `lib/graph-types.ts`.

```ts
export interface AssistantIcon {
  key: string
  label: string
  icon: LucideIcon
}

export const ASSISTANT_ICONS: AssistantIcon[] = [ /* 12 entries */ ]

export const DEFAULT_ICON_KEY = "sparkles"

export function getAssistantIcon(key?: string): LucideIcon {
  return ASSISTANT_ICONS.find((i) => i.key === key)?.icon ?? Sparkles
}
```

### Storage

`assistant.metadata.icon` — a plain string key (e.g., `"brain"`). No backend or TypeScript type changes needed; `metadata` is already typed as `Record<string, unknown>`.

On create and update, the icon key is merged into the metadata payload:
```ts
metadata: { icon: selectedIconKey }
```

### `AssistantForm` changes

- New "Icon" field above the Name field
- Rendered as a trigger button showing the selected icon (32×32 teal square + label)
- Clicking opens a shadcn `Popover` with a 6×2 grid of icon buttons
- Each icon button: 36×36, rounded-md, teal background when selected / muted when not
- Available in both create and edit modes
- Default selection: `sparkles`
- On edit, initializes from `assistant.metadata.icon`

### Assistant card changes (`assistants/page.tsx`)

Replace the hardcoded `<Bot>` icon with the resolved component:

```tsx
const IconComponent = getAssistantIcon(a.metadata?.icon as string)
// ...
<IconComponent size={20} className="text-white" />
```

The teal square container (`w-10 h-10 rounded-md bg-[#2a9d8f]`) stays unchanged.

## Files Changed

| File | Action |
|---|---|
| `lib/icon-map.ts` | Create — icon registry |
| `components/ui/popover.tsx` | Install via `npx shadcn@latest add popover` |
| `components/assistants/AssistantForm.tsx` | Add icon picker field + wire metadata |
| `app/(app)/(picker)/assistants/page.tsx` | Replace hardcoded Bot with dynamic icon |

## Out of Scope

- Custom colors per assistant
- Emoji or image upload as icons
- Icon shown in the chat thread header (can follow in a future iteration)
