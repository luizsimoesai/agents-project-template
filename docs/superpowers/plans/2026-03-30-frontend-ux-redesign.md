# Frontend UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 3-panel layout (icon strip + context panel + main) with a unified sidebar containing an assistant dropdown, thread list, and footer nav; convert AssistantForm from Sheet to Dialog; rewrite the `/assistants` page as a management screen.

**Architecture:** The `AppSidebar` becomes the single source of navigation — it reads `useParams()` for the active assistant/thread from the URL and falls back to local state on other routes. `ContextPanel` is deleted. The `/assistants` route is repurposed from an empty placeholder to a full assistants management page.

**Tech Stack:** Next.js 16.2 App Router, React, TanStack Query, Tailwind CSS v4, shadcn/ui (dialog, button, skeleton), lucide-react, next/font/google.

---

## File Map

| Action | File |
|---|---|
| Modify | `frontend/app/layout.tsx` |
| Modify | `frontend/app/globals.css` |
| Full rewrite | `frontend/components/layout/AppSidebar.tsx` |
| Delete | `frontend/components/layout/ContextPanel.tsx` |
| Modify | `frontend/app/(app)/layout.tsx` |
| Full rewrite | `frontend/app/(app)/assistants/page.tsx` |
| Modify | `frontend/components/assistants/AssistantForm.tsx` |

---

## Task 1: Fix font loading

**Files:**
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/globals.css`

`JetBrains_Mono` is a variable font — specifying an array of weights causes a redundant download. Fix it to use `weight: "variable"`. Verify that both fonts appear in the browser after a fresh dev-server start.

- [ ] **Step 1: Fix JetBrains_Mono weight option**

Replace the font declarations in `frontend/app/layout.tsx`:

```tsx
import type { Metadata } from "next"
import { Bricolage_Grotesque, JetBrains_Mono } from "next/font/google"
import { ThemeProvider } from "next-themes"
import { Toaster } from "sonner"
import { QueryProvider } from "@/components/providers/QueryProvider"
import { AuthProvider } from "@/components/providers/AuthProvider"
import "./globals.css"

const bricolage = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-bricolage",
  display: "swap",
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
  weight: "variable",
})

export const metadata: Metadata = {
  title: "Agent Chat",
  description: "Chat with AI assistants via LangGraph",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${bricolage.variable} ${jetbrainsMono.variable}`}
    >
      <body className="antialiased">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <QueryProvider>
            <AuthProvider>
              {children}
              <Toaster richColors position="top-right" />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 2: Confirm globals.css wires the variables correctly**

The `@theme inline` block in `frontend/app/globals.css` must contain exactly:

```css
--font-sans: var(--font-bricolage);
--font-mono: var(--font-jetbrains-mono);
--font-heading: var(--font-bricolage);
```

No other change needed if those lines are already present.

- [ ] **Step 3: Start dev server and verify**

```bash
cd frontend && npm run dev
```

Open http://localhost:3000, inspect the `<html>` element in DevTools → Computed → `--font-bricolage` must appear as a CSS custom property (e.g. `'Bricolage Grotesque', sans-serif`). Check body text renders in Bricolage Grotesque and monospace elements in JetBrains Mono.

If `--font-bricolage` is missing from the computed styles, the `className` prop is not being applied — check that `bricolage.variable` is included in `<html className={...}>`.

- [ ] **Step 4: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/layout.tsx frontend/app/globals.css
git commit -m "fix: use variable weight for JetBrains Mono"
```

---

## Task 2: Rewrite AppSidebar as unified sidebar

**Files:**
- Full rewrite: `frontend/components/layout/AppSidebar.tsx`

The new sidebar has four sections:
1. **Header** — logo + "nova" button
2. **Assistant dropdown** — native `<select>` listing all assistants; changing it navigates to `/assistants/[id]/threads` and updates local state
3. **Thread list** — threads for the selected assistant; active thread highlighted
4. **Footer** — Assistants page, Profile, theme toggle, Admin (if admin), Sign out

Selected assistant logic: prefer `params.id` from the URL, fall back to local state, then first assistant in list.

- [ ] **Step 1: Write the new AppSidebar**

Replace the entire contents of `frontend/components/layout/AppSidebar.tsx`:

```tsx
"use client"

import { useState } from "react"
import { useRouter, usePathname, useParams } from "next/navigation"
import { useQueryClient } from "@tanstack/react-query"
import {
  Bot, Sun, Moon, LayoutGrid, User, ShieldCheck, LogOut, ChevronDown,
} from "lucide-react"
import { useTheme } from "next-themes"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/lib/store/auth"
import { useAssistants } from "@/lib/hooks/useAssistants"
import { useThreads, useCreateThread } from "@/lib/hooks/useThreads"

export function AppSidebar() {
  const router = useRouter()
  const pathname = usePathname()
  const params = useParams()
  const { theme, setTheme } = useTheme()
  const { user, clearAuth } = useAuthStore()
  const queryClient = useQueryClient()

  const urlAssistantId = params.id as string | undefined
  const urlThreadId = params.threadId as string | undefined
  const [localAssistantId, setLocalAssistantId] = useState<string | undefined>(undefined)

  const { data: assistants } = useAssistants()
  const selectedId = urlAssistantId ?? localAssistantId ?? assistants?.[0]?.assistant_id
  const { data: threads } = useThreads(selectedId)
  const createThread = useCreateThread()

  async function handleNewThread() {
    if (!selectedId) {
      toast.error("Selecione um assistant primeiro")
      return
    }
    try {
      const t = await createThread.mutateAsync({ assistant_id: selectedId })
      router.push(`/assistants/${selectedId}/threads/${t.thread_id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao criar conversa")
    }
  }

  function handleChangeAssistant(id: string) {
    setLocalAssistantId(id)
    router.push(`/assistants/${id}/threads`)
  }

  function handleLogout() {
    queryClient.clear()
    clearAuth()
    router.push("/login")
  }

  return (
    <div className="w-60 shrink-0 border-r border-border/60 bg-sidebar flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/60">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-[#136ddd] flex items-center justify-center shrink-0">
            <Bot size={13} className="text-white" />
          </div>
          <span className="text-sm font-semibold text-foreground">Agent Chat</span>
        </div>
        <button
          onClick={handleNewThread}
          disabled={!selectedId || createThread.isPending}
          className="text-xs px-2 py-1 rounded-md bg-[#136ddd] text-white hover:bg-[#136ddd]/80 transition-colors disabled:opacity-40"
        >
          + nova
        </button>
      </div>

      {/* Assistant dropdown */}
      <div className="px-3 py-2 border-b border-border/40">
        <div className="relative">
          <select
            value={selectedId ?? ""}
            onChange={(e) => handleChangeAssistant(e.target.value)}
            className="w-full bg-accent/40 border border-border/60 rounded-md px-3 py-1.5 text-xs font-mono text-foreground appearance-none cursor-pointer focus:outline-none focus:border-[#136ddd]/50 focus:ring-1 focus:ring-[#136ddd]/20 transition-colors"
          >
            {assistants?.map((a) => (
              <option key={a.assistant_id} value={a.assistant_id}>
                {a.name}
              </option>
            ))}
          </select>
          <ChevronDown
            size={11}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
          />
        </div>
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto py-1.5 px-2">
        <p className="px-2 py-1.5 text-[9px] font-mono uppercase tracking-[0.2em] text-muted-foreground/40 select-none">
          conversas
        </p>
        {threads?.length === 0 && (
          <p className="px-2 py-3 text-xs text-muted-foreground/40 font-mono text-center">
            Nenhuma conversa ainda.
          </p>
        )}
        {threads?.map((t) => (
          <div
            key={t.thread_id}
            onClick={() =>
              router.push(`/assistants/${selectedId}/threads/${t.thread_id}`)
            }
            className={cn(
              "flex items-center gap-2 px-2 py-2 rounded-md cursor-pointer text-xs transition-colors",
              urlThreadId === t.thread_id
                ? "bg-[#136ddd]/10 text-[#c0d8ff]"
                : "text-muted-foreground/70 hover:bg-accent hover:text-foreground"
            )}
          >
            <div
              className={cn(
                "w-1.5 h-1.5 rounded-full shrink-0",
                urlThreadId === t.thread_id ? "bg-[#136ddd]" : "bg-muted-foreground/25"
              )}
            />
            <span className="truncate font-mono">
              {t.thread_name ?? t.thread_id.slice(0, 8) + "…"}
            </span>
          </div>
        ))}
      </div>

      {/* Footer nav */}
      <div className="border-t border-border/60 p-2 space-y-px">
        <FooterItem
          label="Assistants"
          icon={<LayoutGrid size={13} />}
          active={pathname === "/assistants"}
          onClick={() => router.push("/assistants")}
        />
        <FooterItem
          label="Perfil"
          icon={<User size={13} />}
          active={pathname.startsWith("/profile")}
          onClick={() => router.push("/profile")}
        />
        <FooterItem
          label={theme === "dark" ? "Tema claro" : "Tema escuro"}
          icon={theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        />
        {user?.is_admin && (
          <FooterItem
            label="Admin"
            icon={<ShieldCheck size={13} />}
            active={pathname.startsWith("/admin")}
            onClick={() => router.push("/admin")}
          />
        )}
        <FooterItem
          label="Sair"
          icon={<LogOut size={13} />}
          onClick={handleLogout}
          danger
        />
      </div>
    </div>
  )
}

function FooterItem({
  label,
  icon,
  active,
  onClick,
  danger,
}: {
  label: string
  icon: React.ReactNode
  active?: boolean
  onClick?: () => void
  danger?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-xs transition-colors text-left",
        active
          ? "text-[#136ddd] bg-[#136ddd]/10"
          : danger
            ? "text-muted-foreground/50 hover:text-red-400 hover:bg-red-500/10"
            : "text-muted-foreground/50 hover:text-foreground hover:bg-accent"
      )}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run existing tests**

```bash
cd frontend && npx vitest run
```

Expected: all tests pass (AppSidebar has no unit tests, but existing tests must not regress).

- [ ] **Step 4: Commit**

```bash
git add frontend/components/layout/AppSidebar.tsx
git commit -m "feat: rewrite AppSidebar as unified sidebar with assistant dropdown"
```

---

## Task 3: Update AppLayout and delete ContextPanel

**Files:**
- Modify: `frontend/app/(app)/layout.tsx`
- Delete: `frontend/components/layout/ContextPanel.tsx`

- [ ] **Step 1: Remove ContextPanel from the app layout**

Replace the entire contents of `frontend/app/(app)/layout.tsx`:

```tsx
import { AppSidebar } from "@/components/layout/AppSidebar"

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AppSidebar />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  )
}
```

- [ ] **Step 2: Delete ContextPanel.tsx**

```bash
rm frontend/components/layout/ContextPanel.tsx
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors. If ContextPanel is imported anywhere else, those imports will surface as errors — remove them.

- [ ] **Step 4: Run existing tests**

```bash
cd frontend && npx vitest run
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: replace dual-panel layout with unified AppSidebar"
```

---

## Task 4: Rewrite Assistants page as management screen

**Files:**
- Full rewrite: `frontend/app/(app)/assistants/page.tsx`

The `/assistants` route changes from an empty placeholder to a page listing all assistants with create, edit, and delete actions. The `AssistantForm` Dialog is rendered here.

- [ ] **Step 1: Write the management page**

Replace the entire contents of `frontend/app/(app)/assistants/page.tsx`:

```tsx
"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Pencil, Trash2, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useAssistants, useDeleteAssistant } from "@/lib/hooks/useAssistants"
import { AssistantForm } from "@/components/assistants/AssistantForm"
import type { AssistantRead } from "@/lib/types"

export default function AssistantsPage() {
  const { data: assistants, isLoading } = useAssistants()
  const deleteAssistant = useDeleteAssistant()
  const [formOpen, setFormOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<AssistantRead | undefined>(undefined)

  async function handleDelete(id: string) {
    try {
      await deleteAssistant.mutateAsync(id)
      toast.success("Assistant excluído")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao excluir")
    }
  }

  function openCreate() {
    setEditTarget(undefined)
    setFormOpen(true)
  }

  function openEdit(a: AssistantRead) {
    setEditTarget(a)
    setFormOpen(true)
  }

  return (
    <div className="p-8 max-w-2xl">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-border/60">
        <h1 className="text-lg font-semibold">Assistants</h1>
        <Button
          onClick={openCreate}
          size="sm"
          style={{ backgroundColor: "#136ddd" }}
          className="text-white"
        >
          <Plus size={13} className="mr-1.5" />
          Novo assistant
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      ) : assistants?.length === 0 ? (
        <button
          onClick={openCreate}
          className="w-full border border-dashed border-border/50 rounded-lg p-12 text-center hover:border-[#136ddd]/40 hover:bg-[#136ddd]/5 transition-colors"
        >
          <p className="text-sm text-muted-foreground">Nenhum assistant ainda.</p>
          <p className="text-xs text-muted-foreground/50 mt-1">Clique para criar o primeiro.</p>
        </button>
      ) : (
        <div className="space-y-2">
          {assistants?.map((a) => (
            <div
              key={a.assistant_id}
              className="flex items-center justify-between px-4 py-3 bg-card border border-border/60 rounded-lg"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{a.name}</p>
                {(a.context as { model?: string })?.model && (
                  <p className="font-mono text-[11px] text-muted-foreground mt-0.5">
                    {(a.context as { model?: string }).model}
                  </p>
                )}
                {a.description && (
                  <p className="text-xs text-muted-foreground/60 mt-0.5 truncate">
                    {a.description}
                  </p>
                )}
              </div>
              <div className="flex gap-1.5 shrink-0 ml-3">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-foreground"
                  onClick={() => openEdit(a)}
                >
                  <Pencil size={13} />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  onClick={() => handleDelete(a.assistant_id)}
                >
                  <Trash2 size={13} />
                </Button>
              </div>
            </div>
          ))}
          <button
            onClick={openCreate}
            className="w-full flex items-center gap-2 px-4 py-3 border border-dashed border-border/40 rounded-lg hover:border-[#136ddd]/40 hover:bg-[#136ddd]/5 transition-colors"
          >
            <Plus size={13} className="text-muted-foreground/40" />
            <span className="text-xs text-muted-foreground/40">Novo assistant</span>
          </button>
        </div>
      )}

      <AssistantForm open={formOpen} onClose={() => setFormOpen(false)} assistant={editTarget} />
    </div>
  )
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/(app)/assistants/page.tsx
git commit -m "feat: rewrite /assistants as assistant management page"
```

---

## Task 5: Change AssistantForm from Sheet to Dialog

**Files:**
- Modify: `frontend/components/assistants/AssistantForm.tsx`

The `Sheet` component opens from the right edge of the screen, overlapping the main content. A centered `Dialog` is the correct pattern for a form that's always triggered from a button, not from an edge swipe.

- [ ] **Step 1: Replace Sheet with Dialog**

Replace the entire contents of `frontend/components/assistants/AssistantForm.tsx`:

```tsx
"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useCreateAssistant, useUpdateAssistant } from "@/lib/hooks/useAssistants"
import type { AssistantRead } from "@/lib/types"

const schema = z.object({
  name: z.string().min(1, "Nome obrigatório"),
  description: z.string().optional(),
  model: z.string().optional(),
  system_prompt: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface AssistantFormProps {
  open: boolean
  onClose: () => void
  assistant?: AssistantRead
}

export function AssistantForm({ open, onClose, assistant }: AssistantFormProps) {
  const createAssistant = useCreateAssistant()
  const updateAssistant = useUpdateAssistant(assistant?.assistant_id ?? "")

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: assistant?.name ?? "",
      description: assistant?.description ?? "",
      model: (assistant?.context as { model?: string })?.model ?? "",
      system_prompt:
        (assistant?.context as { system_prompt?: string })?.system_prompt ?? "",
    },
  })

  async function onSubmit(data: FormData) {
    const payload = {
      name: data.name,
      description: data.description || undefined,
      context: {
        ...(data.model ? { model: data.model } : {}),
        ...(data.system_prompt ? { system_prompt: data.system_prompt } : {}),
      },
    }
    try {
      if (assistant) {
        await updateAssistant.mutateAsync(payload)
        toast.success("Assistant atualizado")
      } else {
        await createAssistant.mutateAsync(payload)
        toast.success("Assistant criado")
      }
      reset()
      onClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao salvar")
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm">
            {assistant ? "editar assistant" : "novo assistant"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
          <div className="space-y-1">
            <Label>Nome</Label>
            <Input {...register("name")} />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name.message}</p>
            )}
          </div>
          <div className="space-y-1">
            <Label>Descrição</Label>
            <Input {...register("description")} />
          </div>
          <div className="space-y-1">
            <Label className="font-mono text-xs">model</Label>
            <Input
              {...register("model")}
              placeholder="anthropic/claude-sonnet-4-6"
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-1">
            <Label className="font-mono text-xs">system_prompt</Label>
            <Textarea
              {...register("system_prompt")}
              placeholder="You are a helpful assistant..."
              className="font-mono text-sm min-h-28"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="flex-1"
              style={{ backgroundColor: "#136ddd" }}
            >
              {isSubmitting ? "salvando..." : "salvar"}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              cancelar
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run all tests**

```bash
cd frontend && npx vitest run
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/assistants/AssistantForm.tsx
git commit -m "fix: replace Sheet with Dialog in AssistantForm (was opening on wrong side)"
```
