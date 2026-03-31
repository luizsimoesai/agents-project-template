# Assistant Picker & Dual Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current single sidebar layout with (a) a full-screen assistant picker page shown after login, and (b) a dual-panel sidebar shown only in the chat experience.

**Architecture:** Next.js route groups split the `(app)` group into `(picker)` (no sidebar, card grid) and `(chat)` (dual sidebar). `DualSidebar` replaces `AppSidebar`. The picker page is a responsive card grid; the chat layout uses a thin icon rail + wide info panel side by side.

**Tech Stack:** Next.js App Router, React, Tailwind CSS, shadcn/ui, lucide-react, next-themes, zustand, @tanstack/react-query

---

## File Map

| Action | Path |
|--------|------|
| Create | `frontend/app/(app)/(picker)/layout.tsx` |
| Create | `frontend/app/(app)/(picker)/assistants/page.tsx` |
| Create | `frontend/app/(app)/(chat)/layout.tsx` |
| Create | `frontend/components/layout/DualSidebar.tsx` |
| Create | `frontend/app/(app)/(chat)/assistants/[id]/page.tsx` |
| Create | `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx` |
| Create | `frontend/app/(app)/(chat)/assistants/[id]/threads/[threadId]/page.tsx` |
| Create | `frontend/app/(app)/(chat)/admin/page.tsx` |
| Create | `frontend/app/(app)/(chat)/profile/page.tsx` |
| Delete | `frontend/app/(app)/layout.tsx` |
| Delete | `frontend/app/(app)/assistants/page.tsx` |
| Delete | `frontend/app/(app)/assistants/[id]/page.tsx` |
| Delete | `frontend/app/(app)/assistants/[id]/threads/page.tsx` |
| Delete | `frontend/app/(app)/assistants/[id]/threads/[threadId]/page.tsx` |
| Delete | `frontend/app/(app)/admin/page.tsx` |
| Delete | `frontend/app/(app)/profile/page.tsx` |
| Delete | `frontend/components/layout/AppSidebar.tsx` |

---

### Task 1: Create `(picker)` layout — no sidebar

**Files:**
- Create: `frontend/app/(app)/(picker)/layout.tsx`

- [ ] **Step 1: Create the layout file**

```tsx
export default function PickerLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/\(app\)/\(picker\)/layout.tsx
git commit -m "feat: add (picker) route group layout (no sidebar)"
```

---

### Task 2: Create the `DualSidebar` component

**Files:**
- Create: `frontend/components/layout/DualSidebar.tsx`

This component is a client component composed of two adjacent panels: a narrow icon rail (44px) and a wider info/thread panel (180px).

- [ ] **Step 1: Create the component**

```tsx
"use client"

import { useRouter, useParams, usePathname } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import { Bot, LayoutGrid, User, Sun, Moon, ShieldCheck, LogOut, Plus } from "lucide-react"
import { useTheme } from "next-themes"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/lib/store/auth"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { useThreads, useCreateThread } from "@/lib/hooks/useThreads"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export function DualSidebar() {
  const router = useRouter()
  const params = useParams()
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { user, clearAuth } = useAuthStore()
  const queryClient = useQueryClient()

  const assistantId = params.id as string | undefined
  const threadId = params.threadId as string | undefined

  const { data: assistants } = useAssistants()
  const assistant = assistants?.find((a) => a.assistant_id === assistantId)
  const { data: threads } = useThreads(assistantId)
  const createThread = useCreateThread()

  async function handleNewThread() {
    if (!assistantId) return
    try {
      const t = await createThread.mutateAsync({ assistant_id: assistantId })
      router.push(`/assistants/${assistantId}/threads/${t.thread_id}`)
    } catch {
      toast.error("Failed to create conversation")
    }
  }

  function handleLogout() {
    queryClient.clear()
    clearAuth()
    router.push("/login")
  }

  return (
    <div className="flex h-full shrink-0">
      {/* Icon rail — 44px */}
      <TooltipProvider delayDuration={300}>
        <div className="w-11 shrink-0 border-r border-border/60 bg-sidebar flex flex-col items-center py-2 gap-1">
          {/* App logo */}
          <div className="w-7 h-7 rounded-md bg-[#136ddd] flex items-center justify-center mb-2 shrink-0">
            <Bot size={14} className="text-white" />
          </div>

          {/* Back to assistant picker */}
          <RailButton
            icon={<LayoutGrid size={14} />}
            label="Assistants"
            onClick={() => router.push("/assistants")}
          />

          <div className="flex-1" />

          {/* Footer icons */}
          {user?.is_admin && (
            <RailButton
              icon={<ShieldCheck size={14} />}
              label="Admin"
              onClick={() => router.push("/admin")}
              active={pathname.startsWith("/admin")}
            />
          )}
          <RailButton
            icon={<User size={14} />}
            label="Profile"
            onClick={() => router.push("/profile")}
            active={pathname.startsWith("/profile")}
          />
          <RailButton
            icon={theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
            label={theme === "dark" ? "Light theme" : "Dark theme"}
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          />
          <RailButton
            icon={<LogOut size={14} />}
            label="Logout"
            onClick={handleLogout}
            danger
          />
        </div>
      </TooltipProvider>

      {/* Wide panel — 180px */}
      <div className="w-[180px] shrink-0 border-r border-border/60 bg-sidebar flex flex-col h-full">
        {/* Assistant name + description */}
        <div className="px-3 pt-3 pb-2 border-b border-border/40">
          <p className="text-sm font-semibold text-foreground truncate">
            {assistant?.name ?? ""}
          </p>
          {assistant?.description && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
              {assistant.description}
            </p>
          )}
        </div>

        {/* Thread list */}
        <div className="flex-1 overflow-y-auto py-2 px-2">
          <p className="px-2 py-1 text-[9px] font-mono uppercase tracking-[0.2em] text-muted-foreground/40 select-none">
            Conversations
          </p>
          {threads?.length === 0 && (
            <p className="px-2 py-3 text-xs text-muted-foreground/40 font-mono text-center">
              No conversations yet.
            </p>
          )}
          {threads?.map((t) => (
            <button
              key={t.thread_id}
              type="button"
              onClick={() =>
                router.push(`/assistants/${assistantId}/threads/${t.thread_id}`)
              }
              className={cn(
                "w-full text-left flex items-center gap-2 px-2 py-2 rounded-md text-xs transition-colors",
                threadId === t.thread_id
                  ? "bg-[#136ddd]/10 text-[#c0d8ff]"
                  : "text-muted-foreground/70 hover:bg-accent hover:text-foreground"
              )}
            >
              <div
                className={cn(
                  "w-1.5 h-1.5 rounded-full shrink-0",
                  threadId === t.thread_id
                    ? "bg-[#136ddd]"
                    : "bg-muted-foreground/25"
                )}
              />
              <span className="truncate font-mono">
                {t.thread_name ?? `${t.thread_id.slice(0, 8)}…`}
              </span>
            </button>
          ))}
        </div>

        {/* New conversation */}
        <div className="p-2 border-t border-border/40">
          <button
            type="button"
            onClick={handleNewThread}
            disabled={createThread.isPending}
            className="w-full flex items-center gap-2 px-2 py-2 border border-dashed border-border/40 rounded-md text-xs text-muted-foreground/50 hover:text-foreground hover:border-[#136ddd]/40 hover:bg-[#136ddd]/5 transition-colors disabled:opacity-40"
          >
            <Plus size={12} />
            <span>New conversation</span>
          </button>
        </div>
      </div>
    </div>
  )
}

function RailButton({
  icon,
  label,
  onClick,
  active,
  danger,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  active?: boolean
  danger?: boolean
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={onClick}
          className={cn(
            "w-8 h-8 rounded-md flex items-center justify-center transition-colors",
            active
              ? "text-[#136ddd] bg-[#136ddd]/10"
              : danger
                ? "text-muted-foreground/40 hover:text-red-400 hover:bg-red-500/10"
                : "text-muted-foreground/40 hover:text-foreground hover:bg-accent"
          )}
        >
          {icon}
        </button>
      </TooltipTrigger>
      <TooltipContent side="right" className="text-xs">
        {label}
      </TooltipContent>
    </Tooltip>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/layout/DualSidebar.tsx
git commit -m "feat: add DualSidebar component (icon rail + thread panel)"
```

---

### Task 3: Create `(chat)` layout with `DualSidebar`

**Files:**
- Create: `frontend/app/(app)/(chat)/layout.tsx`

- [ ] **Step 1: Create the layout file**

```tsx
import { DualSidebar } from "@/components/layout/DualSidebar"

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <DualSidebar />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/\(app\)/\(chat\)/layout.tsx
git commit -m "feat: add (chat) route group layout with DualSidebar"
```

---

### Task 4: Move chat pages into `(chat)` group

**Files:**
- Create: `frontend/app/(app)/(chat)/assistants/[id]/page.tsx`
- Create: `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx`
- Create: `frontend/app/(app)/(chat)/assistants/[id]/threads/[threadId]/page.tsx`

Content is unchanged from the originals — just re-created under the new path.

- [ ] **Step 1: Create `[id]/page.tsx`**

```tsx
"use client"

import { useParams } from "next/navigation"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Pencil } from "lucide-react"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { AssistantForm } from "@/components/assistants/AssistantForm"
import { Skeleton } from "@/components/ui/skeleton"

export default function AssistantDetailPage() {
  const params = useParams()
  const id = params.id as string
  const { data: assistants, isLoading } = useAssistants()
  const assistant = assistants?.find((a) => a.assistant_id === id)
  const [editOpen, setEditOpen] = useState(false)

  if (isLoading) return <div className="p-6"><Skeleton className="h-8 w-48" /></div>
  if (!assistant) return <div className="p-6 font-mono text-sm text-muted-foreground">assistant not found</div>

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-mono font-semibold" style={{ color: "#136ddd" }}>
          {assistant.name}
        </h2>
        <Button variant="ghost" size="icon" onClick={() => setEditOpen(true)}>
          <Pencil size={14} />
        </Button>
      </div>
      {assistant.description && (
        <p className="text-sm text-muted-foreground">{assistant.description}</p>
      )}
      {(assistant.context as { model?: string })?.model && (
        <p className="font-mono text-xs text-muted-foreground">
          model: {(assistant.context as { model?: string }).model}
        </p>
      )}
      <AssistantForm open={editOpen} onClose={() => setEditOpen(false)} assistant={assistant} />
    </div>
  )
}
```

- [ ] **Step 2: Create `[id]/threads/page.tsx`**

```tsx
export default function ThreadsListPage() {
  return (
    <div className="h-full flex items-center justify-center text-muted-foreground">
      <p className="font-mono text-sm">← select or create a conversation</p>
    </div>
  )
}
```

- [ ] **Step 3: Create `[id]/threads/[threadId]/page.tsx`**

```tsx
"use client"

import { useParams } from "next/navigation"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { ChatView } from "@/components/chat/ChatView"
import { Skeleton } from "@/components/ui/skeleton"

export default function ChatPage() {
  const params = useParams()
  const assistantId = params.id as string
  const threadId = params.threadId as string

  const { data: assistants, isLoading } = useAssistants()
  const assistant = assistants?.find((a) => a.assistant_id === assistantId)

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-64" />
      </div>
    )
  }

  if (!assistant) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="font-mono text-sm text-muted-foreground">assistant not found</p>
      </div>
    )
  }

  return <ChatView threadId={threadId} assistant={assistant} />
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(app\)/\(chat\)/assistants/
git commit -m "feat: move assistant chat pages into (chat) route group"
```

---

### Task 5: Move admin and profile pages into `(chat)` group

**Files:**
- Create: `frontend/app/(app)/(chat)/admin/page.tsx`
- Create: `frontend/app/(app)/(chat)/profile/page.tsx`

- [ ] **Step 1: Create `admin/page.tsx`**

```tsx
"use client"

import { useAuthStore } from "@/lib/store/auth"
import { AdminUserTable } from "@/components/admin/AdminUserTable"
import { ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"

export default function AdminPage() {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)

  if (!user?.is_admin) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <ShieldCheck size={48} className="text-muted-foreground" />
        <p className="font-mono text-sm text-muted-foreground">restricted to administrators</p>
        <Button variant="outline" onClick={() => router.push("/assistants")}>go back</Button>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center gap-2 mb-6">
        <ShieldCheck size={20} style={{ color: "#136ddd" }} />
        <h1 className="text-xl font-mono font-semibold" style={{ color: "#136ddd" }}>
          admin / users
        </h1>
      </div>
      <AdminUserTable />
    </div>
  )
}
```

- [ ] **Step 2: Create `profile/page.tsx`**

```tsx
"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { useProfile, useUpdateProfile } from "@/lib/hooks/useProfile"

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Invalid email"),
})

type FormData = z.infer<typeof schema>

export default function ProfilePage() {
  const { data: user, isLoading } = useProfile()
  const updateProfile = useUpdateProfile()

  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm<FormData>({
      resolver: zodResolver(schema),
      values: { name: user?.name ?? "", email: user?.email ?? "" },
    })

  async function onSubmit(data: FormData) {
    try {
      await updateProfile.mutateAsync(data)
      toast.success("Profile updated")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update profile")
    }
  }

  if (isLoading) {
    return (
      <div className="p-8 max-w-md space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-md">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-xl font-mono font-semibold" style={{ color: "#136ddd" }}>
          profile
        </h1>
        {user?.is_admin && <Badge variant="outline" className="font-mono text-xs">admin</Badge>}
        {!user?.is_active && <Badge variant="destructive" className="font-mono text-xs">inactive</Badge>}
      </div>

      <Card className="border-border">
        <CardHeader>
          <CardTitle className="font-mono text-sm">account details</CardTitle>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <Label>Name</Label>
              <Input {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>Email</Label>
              <Input type="email" {...register("email")} />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>
            <div className="space-y-1">
              <Label className="text-muted-foreground">id</Label>
              <p className="font-mono text-xs text-muted-foreground">{user?.id}</p>
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "saving..." : "save"}
            </Button>
          </CardContent>
        </form>
      </Card>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/\(app\)/\(chat\)/admin/ frontend/app/\(app\)/\(chat\)/profile/
git commit -m "feat: move admin and profile pages into (chat) route group"
```

---

### Task 6: Create the `AssistantPickerPage`

**Files:**
- Create: `frontend/app/(app)/(picker)/assistants/page.tsx`

This is the post-login landing page: a full-screen layout with a header, "Assistants" title, and a responsive card grid. Clicking a card navigates to chat. Edit/delete buttons appear on hover, using `stopPropagation` so they don't trigger card navigation.

- [ ] **Step 1: Create the page**

```tsx
"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Bot, Pencil, Trash2, Plus } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { useAssistants, useDeleteAssistant } from "@/lib/hooks/useAssistants"
import { AssistantForm } from "@/components/assistants/AssistantForm"
import type { AssistantRead } from "@/lib/types"

export default function AssistantPickerPage() {
  const router = useRouter()
  const { data: assistants, isLoading } = useAssistants()
  const deleteAssistant = useDeleteAssistant()
  const [formOpen, setFormOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<AssistantRead | undefined>(undefined)

  function openCreate() {
    setEditTarget(undefined)
    setFormOpen(true)
  }

  function openEdit(a: AssistantRead) {
    setEditTarget(a)
    setFormOpen(true)
  }

  async function handleDelete(id: string) {
    try {
      await deleteAssistant.mutateAsync(id)
      toast.success("Assistant deleted")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete assistant")
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* App header */}
      <header className="flex items-center gap-2.5 px-6 py-3 border-b border-border/60 shrink-0">
        <div className="w-6 h-6 rounded-md bg-[#136ddd] flex items-center justify-center shrink-0">
          <Bot size={13} className="text-white" />
        </div>
        <span className="text-sm font-semibold text-foreground">Agent Chat</span>
      </header>

      {/* Main content */}
      <main className="flex-1 p-8 max-w-5xl w-full mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-foreground">Assistants</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Select an assistant to start a conversation
          </p>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-lg" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3">
            {assistants?.map((a) => (
              <div
                key={a.assistant_id}
                role="button"
                tabIndex={0}
                onClick={() => router.push(`/assistants/${a.assistant_id}/threads`)}
                onKeyDown={(e) =>
                  e.key === "Enter" &&
                  router.push(`/assistants/${a.assistant_id}/threads`)
                }
                className="group relative bg-card border border-border/60 rounded-lg p-3 text-left cursor-pointer hover:border-[#136ddd]/50 hover:bg-[#136ddd]/5 transition-colors"
              >
                {/* Edit / delete — appear on hover */}
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); openEdit(a) }}
                    className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent"
                  >
                    <Pencil size={11} />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); handleDelete(a.assistant_id) }}
                    className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>

                {/* Bot icon */}
                <div className="w-8 h-8 rounded-md bg-[#136ddd] flex items-center justify-center mb-2 shrink-0">
                  <Bot size={16} className="text-white" />
                </div>

                {/* Name */}
                <p className="text-xs font-semibold text-foreground truncate">
                  {a.name}
                </p>

                {/* Description */}
                {a.description && (
                  <p className="text-[10px] text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
                    {a.description}
                  </p>
                )}
              </div>
            ))}

            {/* New assistant card */}
            <button
              type="button"
              onClick={openCreate}
              className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-border/40 rounded-lg p-3 min-h-[7rem] hover:border-[#136ddd]/40 hover:bg-[#136ddd]/5 transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center">
                <Plus size={16} className="text-muted-foreground" />
              </div>
              <span className="text-xs text-muted-foreground">New assistant</span>
            </button>
          </div>
        )}
      </main>

      <AssistantForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        assistant={editTarget}
      />
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/\(app\)/\(picker\)/assistants/
git commit -m "feat: add AssistantPickerPage with responsive card grid"
```

---

### Task 7: Delete old files

Remove the old `(app)` layout and the now-superseded page files. The old `assistants/page.tsx` is replaced by the picker. The chat pages and admin/profile have been re-created in their new locations.

- [ ] **Step 1: Delete old files**

```bash
rm frontend/app/\(app\)/layout.tsx
rm frontend/app/\(app\)/assistants/page.tsx
rm -r frontend/app/\(app\)/assistants/\[id\]
rmdir frontend/app/\(app\)/assistants
rm -r frontend/app/\(app\)/admin
rm -r frontend/app/\(app\)/profile
rm frontend/components/layout/AppSidebar.tsx
```

- [ ] **Step 2: Verify no remaining references to `AppSidebar`**

```bash
grep -r "AppSidebar" frontend/app frontend/components
```

Expected: no output. If any files still import `AppSidebar`, update them to use `DualSidebar`.

- [ ] **Step 3: Commit**

```bash
git add -u
git commit -m "chore: remove old (app) layout, AppSidebar, and superseded page files"
```

---

### Task 8: Smoke test and verify

- [ ] **Step 1: Start the dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: Verify the assistant picker (no sidebar)**

Navigate to `http://localhost:3000/assistants`. Confirm:
- Page shows the header (logo + "Agent Chat") and "Assistants" title
- No sidebar is rendered
- Assistant cards appear in a responsive grid
- Hovering a card reveals pencil and trash icons
- Clicking pencil opens `AssistantForm` in edit mode (form should not navigate away)
- Clicking trash deletes the assistant and shows a toast
- The "New assistant" dashed card is the last item in the grid
- Clicking "New assistant" opens `AssistantForm` in create mode

- [ ] **Step 3: Verify the chat experience (dual sidebar)**

Click any assistant card. Confirm:
- URL is `/assistants/[id]/threads`
- The dual sidebar is rendered: thin icon rail on the far left, wide panel next to it
- Icon rail shows: bot logo, grid icon (Assistants), and footer icons (Admin if admin, Profile, Theme, Logout)
- Wide panel shows: assistant name, description (if present), "Conversations" label, thread list, "New conversation" button
- Hovering icon rail buttons shows a tooltip on the right
- Clicking "← Assistants" (grid icon) navigates back to `/assistants`
- Clicking "New conversation" creates a thread and navigates to it
- Clicking a thread in the list navigates to that thread
- The chat area renders correctly with `ChatView`

- [ ] **Step 4: Verify theme, profile, and admin**

- Click the theme icon — theme toggles between light and dark
- Click the profile icon — navigates to `/profile` with the dual sidebar still visible
- If admin, click the admin icon — navigates to `/admin` with the dual sidebar still visible
- Click the logout icon — clears auth and redirects to `/login`

- [ ] **Step 5: Final commit if any fixes were applied**

```bash
git add -A
git commit -m "fix: post-smoke-test corrections to assistant picker and dual sidebar"
```
