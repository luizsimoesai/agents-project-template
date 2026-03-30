# Frontend UX Redesign

**Date:** 2026-03-30
**Status:** Approved

## Problem

The current frontend has four UX problems:

1. **Fonts not applying** — `--font-bricolage` / `--font-jetbrains-mono` CSS variables not wiring correctly through Tailwind v4's `@theme inline`.
2. **Navigation is awkward** — Two separate panels (icon strip + context panel) create unnecessary friction between assistants and threads.
3. **AssistantForm opens on the wrong side** — `SheetContent` defaults to `side="right"`, pushing the form over the main chat area.
4. **General UX debt** — The three-panel layout (icon strip + context panel + main) feels like a developer scaffold, not a finished product. Inspired by Claude.ai.

---

## Design

### Layout

Replace the current three-panel layout (`AppSidebar` + `ContextPanel` + `main`) with **two panels**: a unified sidebar + main content.

```
┌────────────────────────────────────────────────┐
│  Sidebar (240px)  │  Main content (flex-1)      │
│                   │                             │
│  [⬡ Agent Chat] [+ nova]                        │
│  ┌─────────────┐  │                             │
│  │ GPT Asst ▾  │  │  chat messages / page       │
│  └─────────────┘  │                             │
│  • Conversa 1     │                             │
│  ○ Conversa 2     │                             │
│  ○ Conversa 3     │                             │
│  ─────────────    │                             │
│  ⬚ Assistants     │                             │
│  👤 Perfil        │                             │
│  ☀  Tema          │                             │
│  ⬚ Sair           │                             │
└────────────────────────────────────────────────┘
```

**Sidebar sections (top to bottom):**
- **Header**: Logo + "Nova conversa" button (`+`)
- **Assistant dropdown**: Selects which assistant's threads to show. Changing the assistant shows that assistant's threads. If the selected assistant has no threads, clicking "+" auto-creates one.
- **Thread list**: All threads for the selected assistant, sorted by most recent. Active thread highlighted.
- **Footer**: Links to Assistants page, Profile, Theme toggle, Sign out.

### Routes

| Route | Content |
|---|---|
| `/assistants` | Assistants management page (cards + create/edit/delete) |
| `/assistants/[id]/threads/[threadId]` | Chat view (sidebar shows threads for [id]) |
| `/profile` | Profile page |
| `/admin` | Admin page |

The app layout (`(app)/layout.tsx`) renders the new unified `AppSidebar` instead of `AppSidebar` + `ContextPanel`.

### Assistants Management Page (`/assistants`)

Replaces the current empty placeholder. Shows:
- Page title "Assistants" + "Novo assistant" button (top-right)
- Cards for each assistant: name, model (monospace), description, edit (✎) and delete (🗑) icon buttons
- "Novo assistant" empty card at the bottom

### AssistantForm

Change from `Sheet` to `Dialog` (centered modal). This fixes the form appearing on the wrong side of the screen. The form fields remain the same (name, description, model, system_prompt).

### Fonts

Investigate why Bricolage Grotesque / JetBrains Mono aren't applying. The likely cause is that Tailwind v4's `@theme inline` needs the font variables declared correctly. Fix or fall back to a font pair that works, confirmed via browser devtools inspection.

### Navigation flow

1. User opens app → sidebar shows last-used assistant's threads
2. User clicks a thread → chat loads in main area
3. User clicks "+" → new thread created for current assistant, opens immediately
4. User changes assistant in dropdown → thread list updates. The sidebar highlights the most recent thread but does **not** auto-navigate. User must click a thread to open it. If no threads exist, shows the empty state message.
5. User clicks "Assistants" in footer → navigates to `/assistants` management page
6. User clicks "✎" on an assistant card → Dialog opens pre-filled with assistant data
7. User clicks "Novo assistant" → Dialog opens empty

### Empty states

- No threads for selected assistant: centered message "Nenhuma conversa ainda. Clique em + para começar."
- No assistants at all: redirect to `/assistants` with a prompt to create the first one

---

## Files Changed

| File | Change |
|---|---|
| `app/(app)/layout.tsx` | Remove `ContextPanel`, keep only new `AppSidebar` |
| `components/layout/AppSidebar.tsx` | Full rewrite as unified sidebar (dropdown + thread list + footer) |
| `components/layout/ContextPanel.tsx` | **Delete** (replaced by new sidebar) |
| `app/(app)/assistants/page.tsx` | Rewrite as assistants management page |
| `components/assistants/AssistantForm.tsx` | Change `Sheet` → `Dialog` |
| `app/globals.css` | Fix font variable wiring |
| `app/layout.tsx` | Fix font loading (verify variable names) |

---

## Out of Scope

- Mobile/responsive layout
- Drag-to-reorder threads
- Thread renaming inline
- Search across threads
