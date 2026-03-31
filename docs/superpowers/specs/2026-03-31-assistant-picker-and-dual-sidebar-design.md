# Assistant Picker & Dual Sidebar — Design Spec

**Date:** 2026-03-31  
**Status:** Approved

---

## Overview

After login, the user lands on an assistant picker page (no sidebar) showing their assistants as cards. Clicking a card enters the chat experience, which features a dual sidebar. All UI text must be in English.

---

## Route Architecture

Using Next.js route groups to separate layouts cleanly:

```
app/
├── (app)/
│   ├── (picker)/
│   │   ├── layout.tsx             ← no sidebar, just <main>
│   │   └── assistants/
│   │       └── page.tsx           ← assistant picker (card grid)
│   └── (chat)/
│       ├── layout.tsx             ← renders DualSidebar + <main>
│       └── assistants/
│           └── [id]/
│               ├── page.tsx
│               └── threads/
│                   ├── page.tsx
│                   └── [threadId]/
│                       └── page.tsx
```

The existing `(app)/layout.tsx` (which renders `AppSidebar`) is removed. Each sub-group gets its own `layout.tsx`. The existing `AppSidebar` component is replaced by `DualSidebar`.

---

## Assistant Picker Page

**Route:** `/assistants`  
**File:** `app/(app)/(picker)/assistants/page.tsx`

### Layout
- Simple top header: small app logo (blue square, Bot icon) + "Agent Chat" text
- Page title "Assistants" with subtitle "Select an assistant to start a conversation"
- Responsive card grid: `grid-template-columns: repeat(auto-fill, minmax(140px, 1fr))`

### Cards
Each assistant card contains:
- Colored icon (blue square with Bot icon)
- Assistant name (bold, truncated)
- Description (2 lines max, truncated; omitted if empty)
- Edit button (pencil icon) — opens `AssistantForm` in edit mode
- Delete button (trash icon) — triggers delete with confirmation via `useDeleteAssistant()`

The last item in the grid is always a "New assistant" card:
- Dashed border, centered `+` icon and "New assistant" label
- Clicking opens `AssistantForm` in create mode

### Empty state
When the user has no assistants, only the "New assistant" card is shown.

### Navigation
Clicking an assistant card (not the edit/delete buttons) navigates to `/assistants/[id]/threads`.

### Data
- `useAssistants()` — loads assistant list
- `useDeleteAssistant()` — handles deletion
- `AssistantForm` (existing component) — handles create/edit

---

## Chat Layout — Dual Sidebar

**Route group:** `(chat)`  
**Layout file:** `app/(app)/(chat)/layout.tsx`

The dual sidebar replaces `AppSidebar`. It consists of two adjacent panels rendered inside a flex container alongside `<main>`.

### Icon Rail (thin panel, 44px wide)

Top section:
- App logo (blue square, Bot icon)
- "Back to Assistants" button: grid icon, navigates to `/assistants`

Bottom section (footer icons with tooltips):
- Admin (shield icon) — visible only to `user.is_admin`; navigates to `/admin`
- Profile (user icon) — navigates to `/profile`
- Theme toggle (sun/moon icon) — toggles dark/light theme
- Logout (log-out icon, red) — clears auth, navigates to `/login`

### Wide Panel (180px wide)

Top:
- Assistant name (bold, `text-sm font-semibold`)
- Description below name (if present; `text-xs text-muted-foreground`, truncated to 3 lines)

Middle (scrollable):
- Label "Conversations" (monospace, uppercase, muted)
- List of threads for the current assistant, ordered by most recent
  - Active thread highlighted in blue
  - Each thread shows its name or truncated ID
- "New conversation" button (dashed border) — calls `useCreateThread()`, navigates to new thread

### Data
- `useParams()` — reads `id` (assistantId) and `threadId`
- `useAssistants()` — resolves assistant name and description
- `useThreads(assistantId)` — loads thread list
- `useCreateThread()` — creates a new thread

### New component: `DualSidebar`
**File:** `components/layout/DualSidebar.tsx`

Replaces `AppSidebar`. Composed of two `<div>` elements inside a flex row. Reads params via `useParams()`.

---

## Files Changed

| Action | File |
|--------|------|
| Delete | `app/(app)/layout.tsx` |
| Create | `app/(app)/(picker)/layout.tsx` |
| Move + rewrite | `app/(app)/assistants/page.tsx` → `app/(app)/(picker)/assistants/page.tsx` |
| Create | `app/(app)/(chat)/layout.tsx` |
| Move (unchanged) | `app/(app)/assistants/[id]/page.tsx` → `app/(app)/(chat)/assistants/[id]/page.tsx` |
| Move (unchanged) | `app/(app)/assistants/[id]/threads/page.tsx` → `app/(app)/(chat)/assistants/[id]/threads/page.tsx` |
| Move (unchanged) | `app/(app)/assistants/[id]/threads/[threadId]/page.tsx` → `app/(app)/(chat)/assistants/[id]/threads/[threadId]/page.tsx` |
| Create | `components/layout/DualSidebar.tsx` |
| Delete | `components/layout/AppSidebar.tsx` (replaced by DualSidebar) |

Other pages already inside `(app)` (`/admin`, `/profile`) must also be moved into `(chat)` so they remain within the layout that has the dual sidebar — or into `(picker)` if they should have no sidebar. Given they are utility pages accessed from the icon rail footer, they belong in `(chat)`.

---

## Constraints

- All UI text in English (no Portuguese strings in components)
- Existing `AssistantForm` component is reused as-is
- Existing hooks (`useAssistants`, `useThreads`, `useCreateThread`, `useDeleteAssistant`) are reused as-is
- No new API endpoints required
- The `app/page.tsx` root redirect (`redirect("/assistants")`) remains unchanged
