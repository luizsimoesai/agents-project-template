# Thread Model Selector — Design Spec

**Date:** 2026-05-13  
**Status:** Approved

## Overview

Allow users to choose which LLM model to use per conversation thread. The choice is persisted in thread metadata. Admins manage the available model catalog via the admin panel. The mechanism is graph-agnostic: no individual graph needs to know about model selection.

---

## Backend

### 1. DynamicModel proxy (`agent/utils.py`)

A `BaseChatModel` subclass that reads `model` and `model_base_url` from `config.configurable` at invocation time, making model selection transparent to any graph.

```python
class DynamicModel(BaseChatModel):
    _tools: list = []
    _tool_kwargs: dict = {}

    def _resolve(self, config) -> BaseChatModel:
        cfg = (config or {}).get("configurable", {})
        model_id = cfg.get("model") or os.environ.get("MODEL", DEFAULT_MODEL)
        base_url = cfg.get("model_base_url")
        real = _cached_load(model_id, base_url)  # lru_cache keyed on (model_id, base_url)
        return real.bind_tools(self._tools, **self._tool_kwargs) if self._tools else real

    def bind_tools(self, tools, **kwargs) -> "DynamicModel":
        proxy = DynamicModel()
        proxy._tools = list(tools)
        proxy._tool_kwargs = kwargs
        return proxy

    # Delegates: invoke, ainvoke, stream, astream → _resolve(config)
    # _generate is required by BaseChatModel but never called directly;
    # raise NotImplementedError — all real work goes through invoke/stream.

DYNAMIC_MODEL = DynamicModel()
```

`load_chat_model` gains `base_url: str | None = None`, passed to `init_chat_model` when present.

### 2. Graph updates

Both `agent/graph.py` and `agent/deepagents/graph.py` replace their module-level `_model` with `DYNAMIC_MODEL`:

```python
# before
_model = load_chat_model(os.environ.get("MODEL", "..."))
graph = create_agent(model=_model, ...)

# after
from agent.utils import DYNAMIC_MODEL
graph = create_agent(model=DYNAMIC_MODEL, ...)
```

No other graph changes needed. Future graphs follow the same one-line pattern.

### 3. Context (`agent/context.py`)

Gains `model_base_url: str | None = None`. The `DynamicModel` reads configurable directly and does not depend on Context for model dispatch, but Context documents the supported fields and provides env-var override behaviour for the default model.

### 4. Database — `llm_models` table (Alembic migration)

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | auto-generated |
| `display_name` | str | e.g. "Claude Sonnet 4.6" |
| `model_id` | str | `provider/model` format |
| `provider` | str | `anthropic \| openai \| ollama \| custom` |
| `description` | str? | free text |
| `base_url` | str? | for Ollama or internal servers |
| `is_active` | bool | visible to users |
| `is_default` | bool | pre-selected for new threads (exactly one at a time) |
| `created_at` | datetime | auto |
| `updated_at` | datetime | auto |

New files:
- `src/models/llm_model.py` — SQLAlchemy model (same `table_registry` as `User`)
- `src/schemas/llm_model.py` — Pydantic: `ModelRead`, `ModelCreate`, `ModelUpdate`
- `src/services/model_service.py` — CRUD + `set_default` logic
- `src/api/routes/models.py` — FastAPI router registered in `src/main.py`

### 5. `ModelService` — key logic

`set_default(id)`: in a single transaction, sets `is_default = false` for all other models then `is_default = true` for the target. Ensures exactly one default at all times.

DELETE is blocked (409) if the target model is `is_default=true`; the admin must designate another default first.

### 6. API routes (`/api/v1/models`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/models` | authenticated user | List `is_active=true` models |
| GET | `/models/all` | admin | List all models |
| POST | `/models` | admin | Create model |
| PATCH | `/models/{id}` | admin | Update model |
| DELETE | `/models/{id}` | admin | Delete model (blocked if is_default) |

---

## Frontend

### 1. New UI components (shadcn/ui)

- `components/ui/select.tsx`
- `components/ui/tabs.tsx`

### 2. API layer and hooks

- `lib/types.ts` — add `ModelRead`, `ModelCreate`, `ModelUpdate`
- `lib/api/models.ts` — typed functions for all 5 endpoints
- `lib/hooks/useModels.ts` — two TanStack Query hooks:
  - `useModels()` — fetches active models (`GET /models`), high `staleTime`
  - `useAllModels()` — fetches all models (`GET /models/all`), for admin

### 3. Admin page (`/admin`) — tabbed layout

```
┌─ Usuários ──┬─ Modelos ─────────────────────────────────┐
│             │                                           │
│  (existing  │  [+ Novo Modelo]                          │
│   table)    │  table: display_name | model_id |         │
│             │  provider | base_url | ativo | padrão |   │
│             │  actions: edit / toggle active /          │
│             │  set default / delete                     │
└─────────────┴───────────────────────────────────────────┘
```

New files:
- `components/admin/AdminModelTable.tsx`
- `components/admin/ModelForm.tsx` — Dialog with fields: `display_name`, `model_id`, `provider` (Select), `description`, `base_url`, `is_active` (toggle), `is_default` (toggle)

### 4. `AssistantForm` — remove `model` field

Remove `model` from the Zod schema, form state, and JSX. Model is no longer configured per-assistant.

### 5. `ChatView` — model selector

- `useModels()` provides the active model list
- Local state `selectedModelId` initialized on mount:
  1. `thread.metadata.thread_model` if present
  2. Otherwise `models.find(m => m.is_default)?.model_id`
- shadcn `Select` rendered above `ChatInput`, disabled while `isStreaming`
- On change: calls `updateThreadMetadata(threadId, { thread_model: id, thread_model_base_url: base_url ?? null })`
- On submit: passes `config: { configurable: { model: selectedModelId, model_base_url: selectedModel?.base_url ?? null } }`

`lib/types.ts` — `ThreadRead.metadata` gains typed optional fields `thread_model` and `thread_model_base_url`.

---

## Runtime Flow

```
1. User opens thread
   → frontend reads thread.metadata.thread_model
   → falls back to is_default model if absent

2. User changes model
   → PATCH /threads/{id} saves { thread_model, thread_model_base_url } to metadata

3. User sends message
   → submit({ messages }, { config: { configurable: { model, model_base_url } } })

4. Aegra authenticates and invokes the graph with config.configurable

5. Graph calls DYNAMIC_MODEL (any graph, no changes needed per-graph)

6. DynamicModel._resolve() reads model + model_base_url from configurable
   → loads/caches the real BaseChatModel
   → delegates the call

7. Response streamed back to frontend
```

---

## Out of Scope

- Per-model API key storage (keys remain in environment variables)
- Model usage analytics
- Model switching warning when a thread already has messages
