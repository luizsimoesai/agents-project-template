# Runtime Model Switching — Design Spec

**Date:** 2026-05-19
**Status:** Draft
**Supersedes scope of:** [2026-05-13-thread-model-selector-design.md](2026-05-13-thread-model-selector-design.md) (extends it; thread-level selection still works)

## Overview

Today model selection is locked at thread-creation time and stored in `thread.metadata.thread_model`. This spec lets the user switch the LLM **mid-conversation** without leaving the chat: the model picker moves into `ChatInput`, the choice persists for subsequent messages (sticky), and every AI message records which model produced it so the history stays auditable.

The backend is already capable of per-run model overrides — `configurable_model` middleware reads `ctx.model` from `runtime.context` on every call. This change is mostly frontend, plus one small backend tweak to stamp `model_id` onto each AIMessage.

### Why this design

- **Aegra** passes the request's `context` dict to `graph.astream(context=...)` per run, not per thread. ([docs](https://docs.aegra.dev/reference/configuration#typed-context-with-runtimet-node-level))
- **LangChain** documents this exact pattern: "If your application lets users choose a model (for example using a dropdown in the UI), use middleware to swap the model at runtime." ([docs](https://docs.langchain.com/oss/python/deepagents/models#select-a-model-at-runtime))
- Sticky semantics match user expectations from Claude / ChatGPT, and reuse the existing `useUpdateThreadModel` hook (`frontend/lib/hooks/useThreads.ts:66`) that's currently unwired.

---

## User-visible behaviour

1. In any chat, a small dropdown lives at the top of `ChatInput` (replacing the current read-only `model: X` badge).
2. Picking a different model:
   - Updates the thread's `metadata.thread_model` (and `thread_model_base_url`) — sticky for all future messages of this thread.
   - The next message the user sends uses the new model.
3. Each AI message in the history shows a small mono chip with the model that produced it (e.g. `claude-sonnet-4-6`). Older AI messages (from before this feature) show nothing — graceful fallback.
4. The initial model selector on `ThreadsListPage` (`/assistants/{id}/threads`) stays as-is — picking the model up-front is unchanged. Visual consistency: extract a shared `ModelPicker` component used in both places.

---

## Backend

### Single change: annotate `model_id` in `configurable_model`

`backend/src/agent/model.py:84` — after the handler returns, walk `response.result` and merge `{"model_id": ctx.model}` into each AIMessage's `additional_kwargs`. Don't touch HumanMessage / ToolMessage / SystemMessage. Don't overwrite a pre-existing `model_id` key (defensive).

```python
from langchain_core.messages import AIMessage

@wrap_model_call
async def configurable_model(request, handler):
    ctx = request.runtime.context
    if not ctx or not ctx.model:
        raise ValueError("No model configured. Set MODEL in .env or pass via config.configurable.")
    model = _load(ctx.model, getattr(ctx, "model_base_url", None))
    response = await handler(request.override(model=model))
    for msg in getattr(response, "result", None) or []:
        if isinstance(msg, AIMessage) and "model_id" not in msg.additional_kwargs:
            msg.additional_kwargs["model_id"] = ctx.model
    return response
```

`additional_kwargs` is part of the LangChain message schema and is persisted verbatim by LangGraph's checkpointer (which Aegra uses). No migration required.

No changes to `Context` schema, `aegra.json`, routes, auth, or rate limiting.

---

## Frontend

### Files touched

| File | Change |
|---|---|
| `frontend/components/chat/ModelPicker.tsx` | **NEW.** Extracted shared dropdown. Props: `models`, `value`, `onChange`, optional `compact` for the inline-in-input variant. |
| `frontend/components/chat/ChatInput.tsx` | Replace the read-only `modelLabel` row (lines 44–49) with `<ModelPicker compact />`. Props change: drop `modelLabel`, add `models`, `selectedModelId`, `onModelChange`. |
| `frontend/components/chat/ChatView.tsx` | Hold `selectedModelId` in `useState` (init from `thread.metadata.thread_model` or `initialModel`). `handleSubmit` reads from state, not metadata. Pass picker props to `ChatInput`. Wire `onModelChange` to update state **and** call `useUpdateThreadModel.mutate(...)`. Optimistic — on mutation error, toast and revert state. |
| `frontend/components/chat/ChatMessage.tsx` | Add optional `modelId?: string` prop. When present and `role === "ai"`, render a small mono chip (matches the existing style language). |
| `frontend/app/(app)/(chat)/assistants/[id]/threads/page.tsx` | Replace the inline `<Select>` (lines 65–86) with `<ModelPicker />`. Logic unchanged. |
| `frontend/lib/hooks/useThreads.ts` | No change. `useUpdateThreadModel` already exists. |

### Data flow (one message, mid-conversation switch)

```
User clicks dropdown in ChatInput
  → ChatInput.onModelChange("ollama/llama3:8b")
    → ChatView setSelectedModelId("ollama/llama3:8b")
      + useUpdateThreadModel.mutate({id, modelId, baseUrl})
        → PATCH /threads/{id} { metadata: { thread_model, thread_model_base_url } }

User sends text
  → ChatView.handleSubmit(content)
    → useStream.submit(
        { messages: [{role:"human", content}] },
        { config: { configurable: { model: "ollama/llama3:8b", model_base_url: ... } } }
      )
      → Aegra POST /threads/{id}/runs (SSE)
        → graph.astream(context=Context(model="ollama/llama3:8b", ...))
          → configurable_model picks ctx.model → _load(...) → handler(...)
            → merge additional_kwargs.model_id="ollama/llama3:8b" on AIMessage
              → checkpointer persists

SSE → useStream.messages → ChatView builds displayItems with modelId from additional_kwargs
  → ChatMessage renders chip
```

---

## Error handling & edge cases

- **Model deleted/inactive between runs.** If `thread.metadata.thread_model` references a model no longer in `useModels()`, the Base UI `<Select>` falls back to its placeholder (`"select model..."`) since the `value` has no matching `SelectItem`. The user must pick another model to continue. The backend still accepts any string parseable by `init_chat_model`, so it's a UX safeguard, not a hard block. Showing the stale id as a disabled placeholder item is a future enhancement (YAGNI for now).
- **PATCH /threads fails.** Show toast, revert `selectedModelId` to its previous value. Any message already sent under the new model stays as-is — that's the correct history.
- **Older AIMessages without `model_id`.** Chip not rendered. No migration, no backfill.
- **During streaming.** The chip appears when the AIMessage closes (the chunk carrying `additional_kwargs.model_id` is the final one). Mid-stream the chip is absent — acceptable; injecting from `selectedModelId` while streaming adds local state for marginal gain.
- **First-message flow.** `ThreadsListPage` already passes the chosen model to `createThread` and into the URL (`?model=...`). `ChatView` initializes `selectedModelId` from `initialModel`, then from `thread.metadata.thread_model`. Unchanged.

---

## Tests

### Backend

`backend/tests/test_agent_model.py` (extend or create):

- `configurable_model` annotates `model_id` on AIMessage returned by handler.
- Preserves existing `additional_kwargs` keys; doesn't overwrite a pre-existing `model_id`.
- Doesn't annotate HumanMessage / ToolMessage / SystemMessage.
- Raises `ValueError` when `ctx.model` is empty (existing behaviour, regression guard).

### Frontend (Vitest)

- `ModelPicker.test.tsx` — renders model list, calls `onChange` with selected id.
- `ChatView.test.tsx` (new or extended) — switching model calls `useUpdateThreadModel`; next `submit()` carries the new id in `config.configurable.model`; failed PATCH reverts state and shows toast.
- `ChatMessage.test.tsx` — renders chip when `modelId` provided and `role === "ai"`; renders nothing when absent; renders nothing for human/tool roles.

---

## Out of scope (YAGNI)

- One-shot "use only for this message" toggle.
- Regenerate a specific AI message with a different model.
- Marker in the chat at the point of a model switch.
- Per-model cost / token telemetry.
- Side-by-side model comparison.
- Backfilling `model_id` on historical AIMessages.

Each of these is additive on top of this design and doesn't change the contracts here.

---

## Migration / rollout

None. The backend change is additive (`additional_kwargs` accepts arbitrary keys). The frontend change is feature-only — no schema changes, no env vars, no breaking API contracts. Threads created before this PR keep working: their `thread_model` metadata flows into the new state, and their AIMessages just don't render a chip.
