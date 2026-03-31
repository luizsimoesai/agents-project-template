# Migrate to Aegra Native Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove redundant `/api/v1/assistants` and `/api/v1/threads` routes from the backend and point the frontend directly at Aegra's native LangGraph endpoints, with user scoping enforced via `@auth.on` handlers.

**Architecture:** Aegra already exposes `/assistants` and `/threads` natively and handles persistence. We add `@auth.on` handlers to `jwt.py` so every request is automatically scoped to the authenticated user. The frontend API layer is updated to use these native paths; `useStream()` already talks natively to Aegra so streaming is unaffected.

**Tech Stack:** Python/FastAPI (backend), Next.js/TypeScript (frontend), `@langchain/langgraph-sdk`, `@tanstack/react-query`, Aegra `Auth` from `langgraph_sdk`

---

## File Map

### Backend — delete
- `backend/src/api/routes/assistants.py`
- `backend/src/api/routes/threads.py`
- `backend/src/services/assistant_service.py`
- `backend/src/services/thread_service.py`
- `backend/src/schemas/assistant.py`
- `backend/src/schemas/thread.py`

### Backend — modify
- `backend/src/main.py` — remove assistant/thread router imports and `include_router` calls
- `backend/src/auth/jwt.py` — add `@auth.on` handlers for user scoping

### Frontend — modify
- `frontend/lib/types.ts` — replace `ThreadRead` shape to match Aegra's native format; remove `MessageRead`, `ChatResponse`
- `frontend/lib/api/assistants.ts` — change paths from `/api/v1/assistants` → `/assistants`
- `frontend/lib/api/threads.ts` — change paths to Aegra native; replace `GET /api/v1/threads` with `POST /threads/search`; remove `fetchHistory`
- `frontend/lib/hooks/useThreads.ts` — remove `useThreadHistory`; update `useThreads` filter logic for new thread shape
- `frontend/components/chat/ChatView.tsx` — remove `useThreadHistory` usage; let `useStream` own all messages

---

## Task 1: Add `@auth.on` user-scoping handlers to backend

**Files:**
- Modify: `backend/src/auth/jwt.py`

- [ ] **Step 1: Add `@auth.on` handlers after the existing `@auth.authenticate` function**

Open `backend/src/auth/jwt.py` and append after the `authenticate` function:

```python
@auth.on.assistants.create
async def set_assistant_owner(ctx, value):
    """Inject the authenticated user's identity into assistant metadata on creation."""
    value.setdefault("metadata", {})["owner"] = ctx.user.identity
    return value


@auth.on.assistants.search
async def filter_assistants_by_owner(ctx, value):
    """Restrict assistant list/search results to those owned by the current user."""
    return {"metadata": {"owner": ctx.user.identity}}


@auth.on.threads.create
async def set_thread_owner(ctx, value):
    """Inject the authenticated user's identity into thread metadata on creation."""
    value.setdefault("metadata", {})["owner"] = ctx.user.identity
    return value


@auth.on.threads.search
async def filter_threads_by_owner(ctx, value):
    """Restrict thread search results to those owned by the current user."""
    return {"metadata": {"owner": ctx.user.identity}}
```

- [ ] **Step 2: Verify the server still starts**

```bash
cd backend && uv run aegra dev
```

Expected: server starts without import errors on port 2024. Ctrl+C to stop.

- [ ] **Step 3: Commit**

```bash
git add backend/src/auth/jwt.py
git commit -m "feat: add @auth.on handlers to scope assistants and threads by owner"
```

---

## Task 2: Remove redundant backend routes and services

**Files:**
- Modify: `backend/src/main.py`
- Delete: `backend/src/api/routes/assistants.py`
- Delete: `backend/src/api/routes/threads.py`
- Delete: `backend/src/services/assistant_service.py`
- Delete: `backend/src/services/thread_service.py`
- Delete: `backend/src/schemas/assistant.py`
- Delete: `backend/src/schemas/thread.py`

- [ ] **Step 1: Update `main.py`**

Replace the entire content of `backend/src/main.py` with:

```python
from fastapi import FastAPI

from src.api.routes.auth import router as auth_router
from src.api.routes.users import router as users_router

app = FastAPI()


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "FastAPI is running!"}


# All auth endpoints live under /api/v1/auth (no JWT required).
app.include_router(auth_router, prefix="/api/v1")

# All user CRUD endpoints live under /api/v1/users (JWT required on all routes).
app.include_router(users_router, prefix="/api/v1")
```

- [ ] **Step 2: Delete the six orphaned files**

```bash
rm backend/src/api/routes/assistants.py
rm backend/src/api/routes/threads.py
rm backend/src/services/assistant_service.py
rm backend/src/services/thread_service.py
rm backend/src/schemas/assistant.py
rm backend/src/schemas/thread.py
```

- [ ] **Step 3: Verify linting and server startup**

```bash
cd backend && task lint
uv run aegra dev
```

Expected: no import errors, no references to deleted modules. Ctrl+C to stop.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: remove redundant assistants and threads routes — now served natively by Aegra"
```

---

## Task 3: Update frontend types for Aegra's native thread shape

Aegra's native thread response has metadata nested under a `metadata` object. The current `ThreadRead` type flattens `assistant_id` and `thread_name` as top-level fields — that was a custom mapping done by the deleted service. We also no longer need `MessageRead` or `ChatResponse`.

**Files:**
- Modify: `frontend/lib/types.ts`

- [ ] **Step 1: Replace `ThreadRead`, remove `MessageRead` and `ChatResponse`**

In `frontend/lib/types.ts`, replace the three interfaces:

```typescript
// OLD — remove these:
export interface ThreadRead {
  thread_id: string
  status: "idle" | "busy" | "interrupted" | "error"
  assistant_id: string | null
  thread_name: string | null
  created_at: string
  updated_at: string
}

export interface MessageRead {
  role: string
  content: string
}

export interface ChatResponse {
  thread_id: string
  message: string
  role: string
}
```

With:

```typescript
export interface ThreadRead {
  thread_id: string
  status: "idle" | "busy" | "interrupted" | "error"
  metadata: {
    assistant_id?: string
    thread_name?: string
    owner?: string
    [key: string]: unknown
  }
  created_at: string
  updated_at: string
}
```

- [ ] **Step 2: Verify TypeScript still compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: errors only in files that still use the old shape (threads.ts, hooks, ChatView) — those will be fixed in subsequent tasks.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat: update ThreadRead type to Aegra native shape; remove MessageRead and ChatResponse"
```

---

## Task 4: Update frontend API — assistants

**Files:**
- Modify: `frontend/lib/api/assistants.ts`

- [ ] **Step 1: Replace all `/api/v1/assistants` paths with `/assistants`**

Replace the entire content of `frontend/lib/api/assistants.ts`:

```typescript
import { apiClient } from "./client"
import type { AssistantRead, AssistantCreate, AssistantUpdate } from "@/lib/types"

async function throwOnError(res: Response, fallback: string): Promise<never> {
  let detail = fallback
  try {
    const err = await res.json()
    if (typeof err.detail === "string") detail = err.detail
  } catch {
    // non-JSON body, use fallback
  }
  throw new Error(detail)
}

export async function fetchAssistants(): Promise<AssistantRead[]> {
  const res = await apiClient("/assistants")
  if (!res.ok) return throwOnError(res, "Erro ao buscar assistentes")
  return res.json()
}

export async function fetchAssistant(id: string): Promise<AssistantRead> {
  const res = await apiClient(`/assistants/${id}`)
  if (!res.ok) return throwOnError(res, "Assistente não encontrado")
  return res.json()
}

export async function createAssistant(data: AssistantCreate): Promise<AssistantRead> {
  const res = await apiClient("/assistants", {
    method: "POST",
    body: JSON.stringify({ graph_id: "agent", ...data }),
  })
  if (!res.ok) return throwOnError(res, "Erro ao criar assistente")
  return res.json()
}

export async function updateAssistant(
  id: string,
  data: AssistantUpdate
): Promise<AssistantRead> {
  const res = await apiClient(`/assistants/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) return throwOnError(res, "Erro ao atualizar assistente")
  return res.json()
}

export async function deleteAssistant(id: string): Promise<void> {
  const res = await apiClient(`/assistants/${id}`, { method: "DELETE" })
  if (!res.ok) return throwOnError(res, "Erro ao apagar assistente")
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep assistants
```

Expected: no errors related to assistants files.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/assistants.ts
git commit -m "feat: point assistant API calls to Aegra native /assistants endpoints"
```

---

## Task 5: Update frontend API — threads

**Files:**
- Modify: `frontend/lib/api/threads.ts`

- [ ] **Step 1: Replace `threads.ts` to use native Aegra paths and remove `fetchHistory`**

Replace the entire content of `frontend/lib/api/threads.ts`:

```typescript
import { apiClient } from "./client"
import type { ThreadRead, ThreadCreate } from "@/lib/types"

async function throwOnError(res: Response, fallback: string): Promise<never> {
  let detail = fallback
  try {
    const err = await res.json()
    if (typeof err.detail === "string") detail = err.detail
  } catch {
    // non-JSON body, use fallback
  }
  throw new Error(detail)
}

// POST /threads/search — Aegra filters by owner automatically via @auth.on handler.
// Pass optional metadata filter (e.g. assistant_id) to narrow results further.
export async function fetchThreads(filter?: { assistant_id?: string }): Promise<ThreadRead[]> {
  const body = filter?.assistant_id
    ? { metadata: { assistant_id: filter.assistant_id } }
    : {}
  const res = await apiClient("/threads/search", {
    method: "POST",
    body: JSON.stringify(body),
  })
  if (!res.ok) return throwOnError(res, "Erro ao buscar conversas")
  return res.json()
}

export async function createThread(data: ThreadCreate): Promise<ThreadRead> {
  const res = await apiClient("/threads", {
    method: "POST",
    body: JSON.stringify({
      metadata: {
        assistant_id: data.assistant_id,
        ...(data.thread_name ? { thread_name: data.thread_name } : {}),
      },
    }),
  })
  if (!res.ok) return throwOnError(res, "Erro ao criar conversa")
  return res.json()
}

export async function deleteThread(id: string): Promise<void> {
  const res = await apiClient(`/threads/${id}`, { method: "DELETE" })
  if (!res.ok) return throwOnError(res, "Erro ao apagar conversa")
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep threads
```

Expected: errors only in files that still reference `fetchHistory` or old `ThreadRead` shape (hooks, ChatView) — those will be fixed next.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/threads.ts
git commit -m "feat: point thread API calls to Aegra native endpoints; remove fetchHistory"
```

---

## Task 6: Update `useThreads` hook and remove `useThreadHistory`

**Files:**
- Modify: `frontend/lib/hooks/useThreads.ts`

- [ ] **Step 1: Replace the hooks file**

Replace the entire content of `frontend/lib/hooks/useThreads.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchThreads, createThread, deleteThread } from "@/lib/api/threads"
import type { ThreadCreate } from "@/lib/types"

export const THREADS_KEY = ["threads"]

// assistantId filter is now pushed to the server via POST /threads/search
export function useThreads(assistantId?: string) {
  return useQuery({
    queryKey: [...THREADS_KEY, assistantId],
    queryFn: () => fetchThreads(assistantId ? { assistant_id: assistantId } : undefined),
  })
}

export function useCreateThread() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ThreadCreate) => createThread(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: THREADS_KEY }),
  })
}

export function useDeleteThread() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteThread(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: THREADS_KEY }),
  })
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep useThreads
```

Expected: no errors from this file.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/hooks/useThreads.ts
git commit -m "feat: remove useThreadHistory hook; useThreads filters server-side via Aegra search"
```

---

## Task 7: Update `ChatView` — remove `useThreadHistory`, let `useStream` own history

**Files:**
- Modify: `frontend/components/chat/ChatView.tsx`

- [ ] **Step 1: Replace ChatView to remove history loading and adapt to new ThreadRead shape**

Replace the entire content of `frontend/components/chat/ChatView.tsx`:

```tsx
"use client"

import { useEffect, useRef } from "react"
import { useStream } from "@langchain/langgraph-sdk/react"
import { toast } from "sonner"
import { ChatMessage } from "./ChatMessage"
import { ChatInput } from "./ChatInput"
import { useAuthStore } from "@/lib/store/auth"
import type { Message } from "@langchain/langgraph-sdk"
import type { AssistantRead } from "@/lib/types"

interface ChatViewProps {
  threadId: string
  assistant: AssistantRead
}

function getMessageRole(msg: Message): string {
  if (msg.type === "human") return "human"
  if (msg.type === "ai") return "ai"
  return msg.type ?? "ai"
}

function getMessageContent(msg: Message): string {
  const c = msg.content
  if (typeof c === "string") return c
  return c
    .filter((part): part is { type: "text"; text: string } => part.type === "text")
    .map((part) => part.text)
    .join("")
}

export function ChatView({ threadId, assistant }: ChatViewProps) {
  const accessToken = useAuthStore((s) => s.accessToken)
  const bottomRef = useRef<HTMLDivElement>(null)
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:2024"

  // useStream loads prior messages from the thread automatically when given a threadId.
  const { messages, submit, isLoading: isStreaming, stop } = useStream<{
    messages: Array<{ role: string; content: string }>
  }>({
    apiUrl,
    assistantId: assistant.assistant_id,
    threadId,
    defaultHeaders: accessToken
      ? { Authorization: `Bearer ${accessToken}` }
      : {},
    messagesKey: "messages",
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : "Connection lost"
      toast.error("Streaming error: " + message)
    },
  })

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  function handleSubmit(content: string) {
    submit({ messages: [{ role: "human", content }] })
  }

  const displayMessages = (messages ?? []).map((m) => ({
    role: getMessageRole(m),
    content: getMessageContent(m),
  }))

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto divide-y divide-border/60">
        {displayMessages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground px-6 py-4">
            <p className="font-mono text-sm">start the conversation below</p>
          </div>
        ) : (
          displayMessages.map((msg, i) => (
            <ChatMessage
              key={i}
              role={msg.role}
              content={msg.content}
              isStreaming={
                isStreaming &&
                i === displayMessages.length - 1 &&
                (msg.role === "ai" || msg.role === "assistant")
              }
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput
        onSubmit={handleSubmit}
        onStop={stop}
        isStreaming={isStreaming}
      />
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles cleanly**

```bash
cd frontend && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/chat/ChatView.tsx
git commit -m "feat: remove useThreadHistory from ChatView; useStream owns all message state"
```

---

## Task 8: Fix any remaining consumers of old thread shape

After the type changes in Task 3, any component reading `thread.assistant_id` or `thread.thread_name` directly must be updated to `thread.metadata?.assistant_id` and `thread.metadata?.thread_name`.

**Files:**
- Search and fix all frontend files that reference the old flat fields

- [ ] **Step 1: Find all usages of old flat fields**

```bash
cd frontend && grep -rn "thread\.assistant_id\|thread\.thread_name" --include="*.ts" --include="*.tsx" .
```

Note every file and line number returned.

- [ ] **Step 2: Update each file found**

For each match, replace:
- `thread.assistant_id` → `thread.metadata?.assistant_id`
- `thread.thread_name` → `thread.metadata?.thread_name`

- [ ] **Step 3: Verify TypeScript is clean**

```bash
cd frontend && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "fix: update thread field access to Aegra native metadata shape"
```

---

## Task 9: End-to-end smoke test

- [ ] **Step 1: Start the backend**

```bash
cd backend && uv run aegra dev
```

Expected: server starts on port 2024.

- [ ] **Step 2: Start the frontend**

```bash
cd frontend && npm run dev
```

Expected: Next.js starts on port 3000.

- [ ] **Step 3: Manual smoke test checklist**

Open http://localhost:3000 and verify:

1. Login works → JWT stored
2. Assistants list loads (calls `GET /assistants`)
3. Create assistant → appears in list
4. Edit assistant → changes persist
5. Delete assistant → removed from list
6. Threads list loads (calls `POST /threads/search`)
7. Create thread → appears in list scoped to current user
8. Open thread → ChatView renders with no history loading spinner (loads via `useStream`)
9. Send a message → streams and appears
10. Reload page → prior messages reappear (loaded by `useStream` from Aegra state)
11. Login as a different user → cannot see threads/assistants of the first user

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: verify Aegra native endpoints migration complete"
```
