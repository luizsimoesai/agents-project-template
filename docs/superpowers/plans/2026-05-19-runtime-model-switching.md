# Runtime Model Switching — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow switching the LLM model mid-conversation in the chat UI. The choice is sticky (persists to thread metadata) and every AI message records which model produced it.

**Architecture:** Backend already accepts per-run model overrides via `configurable_model` middleware reading `runtime.context.model`. We add one tweak there: stamp `model_id` on each returned `AIMessage` so the history is auditable. On the frontend, extract a shared `ModelPicker`, embed it in `ChatInput`, drive it from `ChatView` state, persist switches via the existing `useUpdateThreadModel` hook, and render a chip in `ChatMessage` when the persisted `model_id` is present.

**Tech Stack:** Backend — Python 3.12, LangChain `wrap_model_call` middleware, pytest. Frontend — Next.js 16 + React 19, TanStack Query, shadcn `<Select>`, Vitest + `@testing-library/react`, Tailwind v4.

**Spec:** [docs/superpowers/specs/2026-05-19-runtime-model-switching-design.md](../specs/2026-05-19-runtime-model-switching-design.md)

---

## File map

| File | New / Modify | Purpose |
|---|---|---|
| `backend/src/agent/model.py` | Modify | `configurable_model` annotates `additional_kwargs["model_id"]` on returned AIMessages |
| `backend/tests/test_dynamic_model.py` | Modify | Add tests for the new annotation behaviour |
| `frontend/components/chat/ModelPicker.tsx` | New | Shared model dropdown (used by ChatInput and ThreadsListPage) |
| `frontend/components/chat/ModelPicker.test.tsx` | New | Vitest spec for the picker |
| `frontend/components/chat/ChatInput.tsx` | Modify | Replace read-only badge with `<ModelPicker compact />`; new props `models / selectedModelId / onModelChange` |
| `frontend/components/chat/ChatView.tsx` | Modify | Hold `selectedModelId` state; wire `onModelChange` to `useUpdateThreadModel`; pass model into `submit()` from state |
| `frontend/components/chat/ChatView.test.tsx` | New | Vitest spec for switch-and-submit behaviour |
| `frontend/components/chat/ChatMessage.tsx` | Modify | Optional `modelId` prop; renders a small mono chip on AI bubbles when present |
| `frontend/components/chat/ChatMessage.test.tsx` | Modify | Cover the chip rendering |
| `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx` | Modify | Replace inline `<Select>` with `<ModelPicker />` for visual consistency |

No type changes in `frontend/lib/types.ts`. No DB migration. No env vars. The hook `useUpdateThreadModel` already exists in `frontend/lib/hooks/useThreads.ts`.

---

## Task 1: Backend — annotate `model_id` on AIMessages (TDD)

**Files:**
- Modify: `backend/src/agent/model.py:84-95` (the `configurable_model` middleware)
- Test: `backend/tests/test_dynamic_model.py` (extend `TestConfigurableModel`)

Run all backend commands from `backend/`.

- [ ] **Step 1.1: Add the failing test for AIMessage annotation**

Append this test method to the existing `TestConfigurableModel` class in `backend/tests/test_dynamic_model.py`:

```python
    async def test_annotates_model_id_on_ai_messages(self) -> None:
        from langchain_core.messages import AIMessage, HumanMessage

        fake_model = MagicMock(name="loaded_model")
        with patch("src.agent.model._load", return_value=fake_model):
            request, _ = _make_request("openai/gpt-4o")
            ai_msg = AIMessage(content="hello")
            human_msg = HumanMessage(content="hi")
            response = SimpleNamespace(result=[human_msg, ai_msg])

            async def fake_handler(_req):
                return response

            await configurable_model.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]

            assert ai_msg.additional_kwargs.get("model_id") == "openai/gpt-4o"
            # HumanMessage must NOT be touched.
            assert "model_id" not in human_msg.additional_kwargs
```

- [ ] **Step 1.2: Add the failing test for "don't overwrite existing key"**

Append to the same class:

```python
    async def test_does_not_overwrite_existing_model_id(self) -> None:
        from langchain_core.messages import AIMessage

        fake_model = MagicMock()
        with patch("src.agent.model._load", return_value=fake_model):
            request, _ = _make_request("openai/gpt-4o")
            ai_msg = AIMessage(content="hi", additional_kwargs={"model_id": "preset"})
            response = SimpleNamespace(result=[ai_msg])

            async def fake_handler(_req):
                return response

            await configurable_model.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]
            assert ai_msg.additional_kwargs["model_id"] == "preset"
```

- [ ] **Step 1.3: Run the new tests — expect FAIL**

```bash
uv run pytest tests/test_dynamic_model.py::TestConfigurableModel::test_annotates_model_id_on_ai_messages tests/test_dynamic_model.py::TestConfigurableModel::test_does_not_overwrite_existing_model_id -v
```

Expected: both FAIL — `ai_msg.additional_kwargs` is empty because nothing populates it yet.

- [ ] **Step 1.4: Implement the annotation in `configurable_model`**

Replace the entire `configurable_model` function in `backend/src/agent/model.py` (currently lines 84-95) with:

```python
@wrap_model_call  # type: ignore[arg-type]
async def configurable_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    ctx = request.runtime.context
    if not ctx or not ctx.model:
        raise ValueError(
            "No model configured. Set MODEL in .env or pass via config.configurable."
        )
    model = _load(ctx.model, getattr(ctx, "model_base_url", None))
    response = await handler(request.override(model=model))
    # Stamp the user-chosen model id on each AIMessage so the UI can show
    # per-message badges in the chat history. We don't overwrite a value
    # the handler may have set, and we only touch AIMessages.
    for msg in getattr(response, "result", None) or []:
        if isinstance(msg, AIMessage) and "model_id" not in msg.additional_kwargs:
            msg.additional_kwargs["model_id"] = ctx.model
    return response
```

Then add `AIMessage` to the imports at the top of the file. Replace the existing line:

```python
from langchain_core.messages import SystemMessage
```

with:

```python
from langchain_core.messages import AIMessage, SystemMessage
```

- [ ] **Step 1.5: Run the new tests — expect PASS**

```bash
uv run pytest tests/test_dynamic_model.py::TestConfigurableModel -v
```

Expected: all `TestConfigurableModel` tests PASS, including the two new ones.

- [ ] **Step 1.6: Run the full backend test + lint suite**

```bash
task test
```

Expected: PASS, no new lint or mypy errors.

- [ ] **Step 1.7: Commit**

```bash
git add backend/src/agent/model.py backend/tests/test_dynamic_model.py
git commit -m "feat(agent): stamp model_id on AIMessage additional_kwargs

Lets the frontend render a per-message model badge in chat history.
Idempotent — preserves a pre-existing model_id and only touches AIMessages."
```

---

## Task 2: Frontend — create `ModelPicker` component (TDD)

**Files:**
- Create: `frontend/components/chat/ModelPicker.tsx`
- Test: `frontend/components/chat/ModelPicker.test.tsx`

Run all frontend commands from `frontend/`.

- [ ] **Step 2.1: Write the failing tests**

Create `frontend/components/chat/ModelPicker.test.tsx` with:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ModelPicker } from "./ModelPicker"
import type { ModelRead } from "@/lib/types"

const models: ModelRead[] = [
  {
    id: "1", display_name: "Claude Sonnet 4.6", model_id: "anthropic:claude-sonnet-4-6",
    provider: "anthropic", description: null, base_url: null,
    is_active: true, is_default: true,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "2", display_name: "Llama 3", model_id: "ollama/llama3:8b",
    provider: "ollama", description: null, base_url: "http://localhost:11434",
    is_active: true, is_default: false,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
  },
]

describe("ModelPicker", () => {
  it("renders the currently selected model", () => {
    render(<ModelPicker models={models} value="anthropic:claude-sonnet-4-6" onChange={() => {}} />)
    expect(screen.getByRole("combobox")).toHaveTextContent("anthropic:claude-sonnet-4-6")
  })

  it("calls onChange when the user picks a different model", () => {
    const onChange = vi.fn()
    render(<ModelPicker models={models} value="anthropic:claude-sonnet-4-6" onChange={onChange} />)
    // Open the dropdown and pick the second model.
    fireEvent.click(screen.getByRole("combobox"))
    fireEvent.click(screen.getByText("ollama/llama3:8b"))
    expect(onChange).toHaveBeenCalledWith("ollama/llama3:8b")
  })

  it("renders nothing when models list is empty", () => {
    const { container } = render(<ModelPicker models={[]} value="" onChange={() => {}} />)
    expect(container.firstChild).toBeNull()
  })
})
```

- [ ] **Step 2.2: Run the tests — expect FAIL**

```bash
npm run test:run -- components/chat/ModelPicker.test.tsx
```

Expected: FAIL — `ModelPicker` doesn't exist yet.

- [ ] **Step 2.3: Implement `ModelPicker`**

Create `frontend/components/chat/ModelPicker.tsx`:

```tsx
"use client"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { ModelRead } from "@/lib/types"
import { cn } from "@/lib/utils"

interface ModelPickerProps {
  models: ModelRead[]
  value: string
  onChange: (modelId: string) => void
  // `compact` switches to the inline-in-ChatInput variant (smaller, no border chrome).
  compact?: boolean
  disabled?: boolean
}

export function ModelPicker({ models, value, onChange, compact, disabled }: ModelPickerProps) {
  if (!models.length) return null

  return (
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger
        className={cn(
          "font-mono text-xs bg-transparent w-auto p-0 gap-0 overflow-hidden transition-colors",
          compact
            ? "h-6 border-0 hover:bg-muted/30 px-2"
            : "h-7 border-[#2a9d8f]/50 pr-2 hover:border-[#2a9d8f]/80"
        )}
        aria-label={`Model: ${value || "none"}`}
      >
        {!compact && (
          <span className="px-2.5 h-full flex items-center bg-[#2a9d8f]/10 border-r border-[#2a9d8f]/30 text-[#2a9d8f]/80 shrink-0">
            Model
          </span>
        )}
        {compact && <div className="w-1.5 h-1.5 rounded-full bg-[#2a9d8f] shrink-0 mr-1.5" />}
        <SelectValue placeholder="select model..." className={compact ? "min-w-0" : "px-2 min-w-0"} />
      </SelectTrigger>
      <SelectContent>
        {models.map((m) => (
          <SelectItem key={m.model_id} value={m.model_id} className="font-mono text-xs">
            {m.model_id}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
```

- [ ] **Step 2.4: Run the tests — expect PASS**

```bash
npm run test:run -- components/chat/ModelPicker.test.tsx
```

Expected: all three tests PASS.

- [ ] **Step 2.5: Commit**

```bash
git add frontend/components/chat/ModelPicker.tsx frontend/components/chat/ModelPicker.test.tsx
git commit -m "feat(chat): add shared ModelPicker component

Compact variant for inline use in ChatInput; full variant for the
thread-creation page. Renders nothing when the model list is empty."
```

---

## Task 3: Frontend — render `model_id` chip in `ChatMessage` (TDD)

**Files:**
- Modify: `frontend/components/chat/ChatMessage.tsx:6-13` (props), and the AI bubble header area around line 18-33
- Modify: `frontend/components/chat/ChatMessage.test.tsx`

- [ ] **Step 3.1: Add the failing tests**

Append these tests inside the existing `describe("ChatMessage", () => { ... })` block in `frontend/components/chat/ChatMessage.test.tsx`:

```tsx
  it("renders the model chip on AI messages when modelId is provided", () => {
    render(
      <ChatMessage role="ai" content="hi" modelId="anthropic:claude-sonnet-4-6" />
    )
    expect(screen.getByText("anthropic:claude-sonnet-4-6")).toBeInTheDocument()
  })

  it("does not render the chip when modelId is missing", () => {
    render(<ChatMessage role="ai" content="hi" />)
    expect(screen.queryByText(/anthropic:|ollama\//)).not.toBeInTheDocument()
  })

  it("does not render the chip on human messages even if modelId provided", () => {
    render(
      <ChatMessage role="human" content="hi" modelId="anthropic:claude-sonnet-4-6" />
    )
    expect(screen.queryByText("anthropic:claude-sonnet-4-6")).not.toBeInTheDocument()
  })
```

- [ ] **Step 3.2: Run the tests — expect FAIL**

```bash
npm run test:run -- components/chat/ChatMessage.test.tsx
```

Expected: the three new tests FAIL — `modelId` is not a prop yet and the chip doesn't exist.

- [ ] **Step 3.3: Add the `modelId` prop and render the chip**

In `frontend/components/chat/ChatMessage.tsx`, update the props interface (around lines 6-11):

```tsx
interface ChatMessageProps {
  role: string
  content: string
  isStreaming?: boolean
  toolCalls?: RenderedToolCall[]
  modelId?: string
}
```

Update the destructuring on line 13:

```tsx
export function ChatMessage({ role, content, isStreaming = false, toolCalls, modelId }: ChatMessageProps) {
```

Then modify the header `<div className="flex items-center gap-2 mb-2.5">` block (lines 18-33) to append a chip next to the `assistant` / `you` label, **only when** `isAI && modelId`:

```tsx
      <div className="flex items-center gap-2 mb-2.5">
        <div
          className={cn(
            "w-1.5 h-1.5 rounded-full shrink-0",
            isAI ? "bg-[#2a9d8f]" : "bg-muted-foreground/50"
          )}
        />
        <span
          className={cn(
            "font-mono text-[10px] uppercase tracking-[0.18em] font-medium",
            isAI ? "text-[#2a9d8f]" : "text-muted-foreground"
          )}
        >
          {isAI ? "assistant" : "you"}
        </span>
        {isAI && modelId && (
          <span className="font-mono text-[10px] text-muted-foreground/60 px-1.5 py-0.5 rounded bg-muted/40 border border-border/40">
            {modelId}
          </span>
        )}
      </div>
```

- [ ] **Step 3.4: Run the tests — expect PASS**

```bash
npm run test:run -- components/chat/ChatMessage.test.tsx
```

Expected: all tests in `ChatMessage.test.tsx` PASS (existing + 3 new).

- [ ] **Step 3.5: Commit**

```bash
git add frontend/components/chat/ChatMessage.tsx frontend/components/chat/ChatMessage.test.tsx
git commit -m "feat(chat): render per-message model chip on AI bubbles

Reads modelId prop and shows a small mono chip next to the assistant
label. Hidden when modelId is missing (graceful fallback for older
messages)."
```

---

## Task 4: Frontend — refactor `ChatInput` to host `ModelPicker`

**Files:**
- Modify: `frontend/components/chat/ChatInput.tsx`

This step has no new unit test of its own — `ChatInput`'s behaviour is exercised by the upcoming `ChatView` test in Task 5. We do verify the existing tests still pass.

- [ ] **Step 4.1: Replace `ChatInput` with the new props shape**

Overwrite `frontend/components/chat/ChatInput.tsx` with:

```tsx
"use client"

import { useRef, useState, useEffect } from "react"
import { Square, ArrowUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ModelPicker } from "./ModelPicker"
import type { ModelRead } from "@/lib/types"
import { cn } from "@/lib/utils"

interface ChatInputProps {
  onSubmit: (message: string) => void
  onStop: () => void
  isStreaming: boolean
  disabled?: boolean
  centered?: boolean
  // Optional model picker — when `models` is non-empty we render the dropdown.
  models?: ModelRead[]
  selectedModelId?: string
  onModelChange?: (modelId: string) => void
}

export function ChatInput({
  onSubmit,
  onStop,
  isStreaming,
  disabled,
  centered,
  models,
  selectedModelId,
  onModelChange,
}: ChatInputProps) {
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

  const showPicker = !!models && models.length > 0 && !!onModelChange

  return (
    <div className={centered ? "w-full" : "border-t border-border/60 px-4 py-3"}>
      <div className="bg-card border border-border rounded-xl shadow-sm focus-within:border-[#2a9d8f]/50 focus-within:ring-2 focus-within:ring-[#2a9d8f]/10 transition-all overflow-hidden">
        {showPicker && (
          <div className="flex items-center px-2 py-1 border-b border-border/40 bg-muted/20">
            <ModelPicker
              compact
              models={models!}
              value={selectedModelId ?? ""}
              onChange={onModelChange!}
              disabled={isStreaming}
            />
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
              "resize-none min-h-12 max-h-40 font-mono text-sm flex-1",
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

Key changes from the previous version:
- Removed the `modelLabel` prop and the read-only badge row (old lines 44-49).
- Added `models / selectedModelId / onModelChange`; renders the picker only when all three are present and the list is non-empty.
- Picker is disabled during streaming so users can't trigger a metadata mutation while a run is in flight.

- [ ] **Step 4.2: Run the entire frontend test suite — expect PASS (no regressions)**

```bash
npm run test:run
```

Expected: every test passes. (ChatView and ThreadsListPage still pass `modelLabel`? They will — TypeScript will error at compile time. We fix call sites in the next tasks. But for now the suite may compile because old callers haven't been touched and only pass `modelLabel`, which TypeScript flags as a type error.)

If TypeScript complains about `modelLabel` at unchanged call sites (`ChatView.tsx`, `ThreadsListPage`), that is expected — Task 5 and Task 7 fix them. To run tests during the interim, this command is enough; Vitest does not block on TS errors. But verify the failure surface is only those two files:

```bash
npx tsc --noEmit | head -20
```

Expected: errors only in `ChatView.tsx` and `app/(app)/(chat)/assistants/[id]/threads/page.tsx`, related to `modelLabel`. Note these for resolution in Tasks 5 and 7. Do not commit yet — proceed to Task 5 so the codebase compiles end-to-end before the commit there.

---

## Task 5: Frontend — wire `ChatView` for stateful, sticky model switching (TDD)

**Files:**
- Modify: `frontend/components/chat/ChatView.tsx`
- Create: `frontend/components/chat/ChatView.test.tsx`

- [ ] **Step 5.1: Write the failing test**

Create `frontend/components/chat/ChatView.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createElement } from "react"
import { ChatView } from "./ChatView"
import type { AssistantRead, ModelRead, ThreadRead } from "@/lib/types"

// ---- Mocks -----------------------------------------------------------------
const submitMock = vi.fn()

vi.mock("@langchain/langgraph-sdk/react", () => ({
  useStream: () => ({
    messages: [],
    submit: submitMock,
    isLoading: false,
    stop: () => {},
  }),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}))

const updateMetadataMock = vi.fn().mockResolvedValue({})
vi.mock("@/lib/api/threads", () => ({
  fetchThreads: vi.fn().mockResolvedValue([
    {
      thread_id: "t1",
      status: "idle",
      metadata: {
        thread_assistant_id: "a1",
        thread_model: "anthropic:claude-sonnet-4-6",
        thread_model_base_url: null,
      },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    } satisfies ThreadRead,
  ]),
  fetchThreadState: vi.fn().mockResolvedValue([]),
  updateThreadMetadata: (...args: unknown[]) => updateMetadataMock(...args),
  deleteThread: vi.fn(),
  createThread: vi.fn(),
}))

const models: ModelRead[] = [
  {
    id: "1", display_name: "Sonnet 4.6", model_id: "anthropic:claude-sonnet-4-6",
    provider: "anthropic", description: null, base_url: null,
    is_active: true, is_default: true,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "2", display_name: "Llama 3", model_id: "ollama/llama3:8b",
    provider: "ollama", description: null, base_url: "http://localhost:11434",
    is_active: true, is_default: false,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
  },
]

vi.mock("@/lib/hooks/useModels", () => ({
  useModels: () => ({ data: models, isLoading: false }),
}))

vi.mock("@/lib/store/auth", () => ({
  useAuthStore: ((selector: (s: { accessToken: string }) => unknown) =>
    selector({ accessToken: "token" })) as unknown as typeof import("@/lib/store/auth").useAuthStore,
}))

// ---- Helpers ---------------------------------------------------------------
const assistant: AssistantRead = {
  assistant_id: "a1", name: "A", description: null, graph_id: "basic_agent",
  config: {}, context: {}, metadata: {}, version: 1,
  created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
}

function wrap(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(createElement(QueryClientProvider, { client }, ui))
}

beforeEach(() => {
  submitMock.mockClear()
  updateMetadataMock.mockClear()
})

// ---- Tests -----------------------------------------------------------------
describe("ChatView model switching", () => {
  it("switching model persists to thread metadata and uses it in the next submit", async () => {
    wrap(<ChatView threadId="t1" assistant={assistant} />)

    // Wait for the picker to render with the thread's current model.
    await waitFor(() =>
      expect(screen.getByRole("combobox")).toHaveTextContent("anthropic:claude-sonnet-4-6")
    )

    // Switch to llama3.
    fireEvent.click(screen.getByRole("combobox"))
    fireEvent.click(screen.getByText("ollama/llama3:8b"))

    // PATCH was fired with the new model + its base_url.
    await waitFor(() =>
      expect(updateMetadataMock).toHaveBeenCalledWith("t1", {
        thread_model: "ollama/llama3:8b",
        thread_model_base_url: "http://localhost:11434",
      })
    )

    // Type a message and send it.
    const textarea = screen.getByPlaceholderText(/Message/i)
    fireEvent.change(textarea, { target: { value: "with llama" } })
    fireEvent.keyDown(textarea, { key: "Enter" })

    // submit() carried the new model in config.configurable.
    expect(submitMock).toHaveBeenCalledWith(
      { messages: [{ role: "human", content: "with llama" }] },
      { config: { configurable: { model: "ollama/llama3:8b", model_base_url: "http://localhost:11434" } } }
    )
  })
})
```

- [ ] **Step 5.2: Run the test — expect FAIL**

```bash
npm run test:run -- components/chat/ChatView.test.tsx
```

Expected: FAIL — the current `ChatView` still reads model from thread metadata each submit and doesn't render the picker.

- [ ] **Step 5.3: Rewrite `ChatView` to hold `selectedModelId` state**

Replace the body of `frontend/components/chat/ChatView.tsx` (everything after the imports) with a version that:
1. Adds `selectedModelId` / `setSelectedModelId` state, seeded from thread metadata or `initialModel`.
2. Wires `useModels()` to populate the picker.
3. Defines `handleModelChange` — updates state and calls `useUpdateThreadModel`; on error, reverts state via toast.
4. Sends `selectedModelId` (not the metadata) into every `submit()`.
5. Passes `modelId` (read from `additional_kwargs.model_id`) into each rendered `ChatMessage`.

Full file:

```tsx
"use client"

import type { Route } from "next"
import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useStream } from "@langchain/langgraph-sdk/react"
import { toast } from "sonner"
import { ChatMessage } from "./ChatMessage"
import { ChatInput } from "./ChatInput"
import { useAuthStore } from "@/lib/store/auth"
import { API_URL } from "@/lib/api/client"
import {
  useThreadState,
  useUpdateThreadName,
  useThread,
  useUpdateThreadModel,
} from "@/lib/hooks/useThreads"
import { useModels } from "@/lib/hooks/useModels"
import type { Message, AIMessage, ToolMessage } from "@langchain/langgraph-sdk"
import type { AssistantRead } from "@/lib/types"
import type { RenderedToolCall } from "./ToolCallBadge"

interface ChatViewProps {
  threadId: string
  assistant: AssistantRead
  initialMessage?: string
  initialModel?: string
  initialModelBaseUrl?: string
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

// AIMessage.additional_kwargs is loosely typed in the SDK; pull model_id safely.
function getModelId(msg: Message): string | undefined {
  const kwargs = (msg as { additional_kwargs?: Record<string, unknown> }).additional_kwargs
  const v = kwargs?.model_id
  return typeof v === "string" ? v : undefined
}

function buildHistoricToolCalls(
  aiMsg: AIMessage,
  allMessages: Message[]
): RenderedToolCall[] {
  const rawCalls = aiMsg.tool_calls ?? []
  if (rawCalls.length === 0) return []

  const toolMessages = allMessages.filter(
    (m): m is ToolMessage => m.type === "tool"
  )

  return rawCalls.map((call, i) => {
    const toolMsg = toolMessages.find((tm) => tm.tool_call_id === call.id)
    return {
      id: call.id ?? `${aiMsg.id}-${i}`,
      name: call.name,
      args: (call.args ?? {}) as Record<string, unknown>,
      state: toolMsg ? "completed" : "pending",
      result: toolMsg
        ? typeof toolMsg.content === "string"
          ? toolMsg.content
          : JSON.stringify(toolMsg.content)
        : undefined,
    } satisfies RenderedToolCall
  })
}

export function ChatView({
  threadId,
  assistant,
  initialMessage,
  initialModel,
  initialModelBaseUrl,
}: ChatViewProps) {
  const accessToken = useAuthStore((s) => s.accessToken)
  const bottomRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const initialMessageSent = useRef(false)
  const threadNameSet = useRef(false)
  const updateThreadName = useUpdateThreadName()
  const updateThreadModel = useUpdateThreadModel()

  const { data: historicMessages } = useThreadState(threadId)
  const { data: thread } = useThread(threadId)
  const { data: models } = useModels()

  // selectedModelId is the source of truth for the *next* submit().
  // Initialized from thread metadata; falls back to initialModel from URL.
  const [selectedModelId, setSelectedModelId] = useState<string>("")
  const [selectedModelBaseUrl, setSelectedModelBaseUrl] = useState<string | null>(null)
  const modelInitialized = useRef(false)

  useEffect(() => {
    if (modelInitialized.current) return
    const fromMeta = thread?.metadata?.thread_model as string | undefined
    const fromMetaBaseUrl =
      (thread?.metadata?.thread_model_base_url as string | null | undefined) ?? null
    const seed = fromMeta ?? initialModel ?? ""
    const seedBaseUrl = fromMeta ? fromMetaBaseUrl : (initialModelBaseUrl ?? null)
    if (seed) {
      setSelectedModelId(seed)
      setSelectedModelBaseUrl(seedBaseUrl)
      modelInitialized.current = true
    }
  }, [thread, initialModel, initialModelBaseUrl])

  function handleModelChange(modelId: string) {
    const previous = { id: selectedModelId, baseUrl: selectedModelBaseUrl }
    const next = models?.find((m) => m.model_id === modelId)
    const baseUrl = next?.base_url ?? null
    setSelectedModelId(modelId)
    setSelectedModelBaseUrl(baseUrl)
    updateThreadModel.mutate(
      { id: threadId, modelId, baseUrl },
      {
        onError: (err) => {
          setSelectedModelId(previous.id)
          setSelectedModelBaseUrl(previous.baseUrl)
          const detail = err instanceof Error ? err.message : "Failed to persist model"
          toast.error(detail)
        },
      }
    )
  }

  const { messages, submit, isLoading: isStreaming, stop } = useStream<{
    messages: Array<{ role: string; content: string }>
  }>({
    apiUrl: API_URL,
    assistantId: assistant.assistant_id,
    threadId,
    defaultHeaders: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    messagesKey: "messages",
    onError: (err: unknown) => {
      if (!useAuthStore.getState().accessToken) return
      const message = err instanceof Error ? err.message : "Connection lost"
      toast.error("Streaming error: " + message)
    },
  })

  // Auto-submit the first message when arriving from the "new thread" flow
  useEffect(() => {
    if (!initialMessage || initialMessageSent.current) return
    initialMessageSent.current = true
    const modelForFirst = initialModel ?? selectedModelId
    submit(
      { messages: [{ role: "human", content: initialMessage }] },
      modelForFirst
        ? {
            config: {
              configurable: {
                model: modelForFirst,
                model_base_url: initialModelBaseUrl ?? selectedModelBaseUrl ?? null,
              },
            },
          }
        : undefined
    )
    router.replace(window.location.pathname as Route, { scroll: false })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // After the first AI response lands, name the thread from the first human message
  useEffect(() => {
    if (isStreaming || threadNameSet.current) return
    const msgs =
      streamMessages.length > 0
        ? streamMessages
        : ((historicMessages ?? []) as Message[])
    const humanMsg = msgs.find((m) => getMessageRole(m) === "human")
    const aiMsg = msgs.find((m) => getMessageRole(m) === "ai" || getMessageRole(m) === "assistant")
    if (!humanMsg || !aiMsg) return
    const candidate = getMessageContent(humanMsg).slice(0, 50).trim()
    if (!candidate) return
    threadNameSet.current = true
    updateThreadName.mutate({ id: threadId, name: candidate })
  }, [isStreaming]) // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, historicMessages])

  function handleSubmit(content: string) {
    submit(
      { messages: [{ role: "human", content }] },
      selectedModelId
        ? {
            config: {
              configurable: {
                model: selectedModelId,
                model_base_url: selectedModelBaseUrl,
              },
            },
          }
        : undefined
    )
  }

  const streamMessages = messages ?? []
  const historic = (historicMessages ?? []) as Message[]
  const usingStream = streamMessages.length > 0

  type DisplayItem = {
    role: string
    content: string
    toolCalls: RenderedToolCall[]
    isLast: boolean
    modelId?: string
  }

  const displayItems: DisplayItem[] = (() => {
    const source = usingStream ? streamMessages : historic
    const visible = source.filter((m) => m.type !== "tool" && m.type !== "system")

    return visible.map((msg, i) => {
      let toolCalls: RenderedToolCall[] = []
      if (msg.type === "ai") {
        toolCalls = buildHistoricToolCalls(msg as AIMessage, source)
      }
      return {
        role: getMessageRole(msg),
        content: getMessageContent(msg),
        toolCalls,
        isLast: i === visible.length - 1,
        modelId: getModelId(msg),
      }
    })
  })()

  return (
    <div className="relative flex flex-col h-full">
      <div className="flex-1 overflow-y-auto divide-y divide-border/60">
        {displayItems.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground px-6 py-4">
            <p className="font-mono text-sm">What can I help you with today?</p>
          </div>
        ) : (
          displayItems.map((item, i) => (
            <ChatMessage
              key={i}
              role={item.role}
              content={item.content}
              toolCalls={item.toolCalls}
              modelId={item.modelId}
              isStreaming={
                isStreaming &&
                item.isLast &&
                (item.role === "ai" || item.role === "assistant")
              }
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <ChatInput
        onSubmit={handleSubmit}
        onStop={stop}
        isStreaming={isStreaming}
        models={models}
        selectedModelId={selectedModelId}
        onModelChange={handleModelChange}
      />
    </div>
  )
}
```

- [ ] **Step 5.4: Run the new test — expect PASS**

```bash
npm run test:run -- components/chat/ChatView.test.tsx
```

Expected: the switch-and-submit test PASSES.

- [ ] **Step 5.5: Run the full frontend test suite**

```bash
npm run test:run
```

Expected: all PASS. (The only remaining TS error after Task 4 — the inline `modelLabel` reference in `ChatView` — was fixed by this rewrite.)

- [ ] **Step 5.6: Type-check the frontend**

```bash
npx tsc --noEmit
```

Expected: errors only in `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx` if any (Task 6 fixes that page). If errors remain elsewhere, stop and resolve.

- [ ] **Step 5.7: Commit**

```bash
git add frontend/components/chat/ChatInput.tsx frontend/components/chat/ChatView.tsx frontend/components/chat/ChatView.test.tsx
git commit -m "feat(chat): mid-conversation model switching with sticky persistence

ChatInput hosts a compact ModelPicker; ChatView holds selectedModelId
state, wires switches to useUpdateThreadModel (sticky), and reads
per-message model_id from additional_kwargs into the ChatMessage chip.

Reverts state and shows a toast if the metadata PATCH fails."
```

---

## Task 6: Frontend — use `ModelPicker` on the thread-creation page

**Files:**
- Modify: `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx:65-86` (replace the inline `<Select>` block)

- [ ] **Step 6.1: Replace the inline picker**

In `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx`, replace the imports block (top) — change:

```tsx
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
```

to:

```tsx
import { ModelPicker } from "@/components/chat/ModelPicker"
```

Then replace the `{models && models.length > 0 && selectedModelId && (...)}` block (currently lines 65-86) with:

```tsx
        {models && models.length > 0 && selectedModelId && (
          <div className="flex justify-center">
            <ModelPicker
              models={models}
              value={selectedModelId}
              onChange={(id) => handleModelChange(id)}
            />
          </div>
        )}
```

`handleModelChange` already exists in this file and accepts a string — no signature changes.

- [ ] **Step 6.2: Type-check the frontend**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors anywhere.

- [ ] **Step 6.3: Run the full frontend test suite**

```bash
npm run test:run
```

Expected: all PASS.

- [ ] **Step 6.4: Commit**

```bash
git add frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx
git commit -m "refactor(chat): use shared ModelPicker on thread-creation page

Drops the inline shadcn Select for visual consistency with ChatInput."
```

---

## Task 7: Manual smoke test

The unit tests cover wiring. This last check exercises the live backend → frontend round-trip and verifies the chip actually shows the model the user picked.

- [ ] **Step 7.1: Start backend and frontend**

In one terminal:

```bash
cd backend && uv run aegra dev
```

In another:

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000` and log in.

- [ ] **Step 7.2: Test mid-conversation switching**

1. Open an existing assistant and create a new thread (model A — pick whatever's the current default).
2. Send a message; confirm an AI reply with the model A chip appears.
3. Open the model picker inside `ChatInput`; switch to model B.
4. Send another message; confirm the new AI bubble shows the **model B** chip while the prior AI bubble still shows model A.
5. Refresh the page; confirm both chips persist (read from `additional_kwargs.model_id` via thread state).
6. Verify `thread.metadata.thread_model` reflects model B by reopening the thread later — the picker shows model B as the current value.

- [ ] **Step 7.3: Test failure path (optional but recommended)**

Stop the backend, switch model in the UI, verify a toast appears and the picker reverts to the previous value.

- [ ] **Step 7.4: No commit**

This step is verification, not code change. If any of the manual checks fails, file an issue or return to the relevant task.

---

## Self-review checklist (run after the plan, before handing off)

- **Spec coverage:**
  - "Sticky persistence" → Task 5 (`handleModelChange` calls `useUpdateThreadModel`). ✓
  - "Model picker inside ChatInput" → Tasks 2, 4, 5. ✓
  - "Per-message chip" → Tasks 1, 3, 5 (`additional_kwargs.model_id`, `ChatMessage` chip, `ChatView` passes `modelId`). ✓
  - "ModelPicker reused on ThreadsListPage" → Task 6. ✓
  - "Graceful fallback for older messages" → Task 3 (chip hidden when `modelId` missing). ✓
  - "Disabled picker during streaming" → Task 4 (`disabled={isStreaming}`). ✓
  - "Error toast + revert on PATCH failure" → Task 5 (`onError` in mutation). ✓
  - "No migration / no env vars" → confirmed; no DB or config touched. ✓

- **No placeholders.** Every step has the exact code or command. No "add appropriate error handling" or "similar to Task N". ✓
- **Type consistency.**
  - `ModelPicker` props (`models`, `value`, `onChange`, `compact`, `disabled`) match its usages in `ChatInput` and `ThreadsListPage`. ✓
  - `ChatInput`'s new props (`models`, `selectedModelId`, `onModelChange`) match the call site in `ChatView`. ✓
  - `ChatMessage`'s new `modelId` prop matches the `DisplayItem.modelId` passed in `ChatView`. ✓
  - `useUpdateThreadModel.mutate` argument shape (`{ id, modelId, baseUrl }`) matches the hook signature in `frontend/lib/hooks/useThreads.ts:66`. ✓
  - Backend `AIMessage.additional_kwargs["model_id"]` (string) matches what `ChatView.getModelId` reads. ✓
