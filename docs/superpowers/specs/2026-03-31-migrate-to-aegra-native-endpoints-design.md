# Design: Migrate to Aegra Native Endpoints

**Date:** 2026-03-31
**Status:** Approved

## Summary

Remove redundant `/api/v1/assistants` and `/api/v1/threads` routes from the FastAPI backend and redirect the frontend to Aegra's native LangGraph endpoints. Authentication and user scoping are handled via `@auth.on` handlers already supported by Aegra. The backend retains only auth and user management routes.

---

## Backend Changes

### Delete

| File | Reason |
|------|--------|
| `src/api/routes/assistants.py` | Fully covered by Aegra native `/assistants` |
| `src/api/routes/threads.py` | Fully covered by Aegra native `/threads` |
| `src/services/assistant_service.py` | Only served the deleted router |
| `src/services/thread_service.py` | Only served the deleted router |

### Update `src/main.py`

Remove imports and `app.include_router()` calls for `assistants_router` and `threads_router`.

### Update `src/auth/jwt.py`

Add `@auth.on` handlers for automatic user scoping:

```python
@auth.on.assistants.create
async def set_assistant_owner(ctx, value):
    value.setdefault("metadata", {})["owner"] = ctx.user.identity
    return value

@auth.on.assistants.search
async def filter_assistants_by_owner(ctx, value):
    return {"metadata": {"owner": ctx.user.identity}}

@auth.on.threads.create
async def set_thread_owner(ctx, value):
    value.setdefault("metadata", {})["owner"] = ctx.user.identity
    return value

@auth.on.threads.search
async def filter_threads_by_owner(ctx, value):
    return {"metadata": {"owner": ctx.user.identity}}
```

### Schemas/models to delete (if orphaned after route deletion)

- `src/schemas/assistant.py` — only used by deleted routes
- `src/schemas/thread.py` — only used by deleted routes

---

## Frontend Changes

### `lib/api/client.ts`

No change — token refresh still calls `/api/v1/auth/refresh`.

### `lib/api/assistants.ts`

Change base path from `/api/v1/assistants` → `/assistants`.
Response shape changes: Aegra returns raw assistant object, same fields.

### `lib/api/threads.ts`

| Before | After |
|--------|-------|
| `GET /api/v1/threads` | `POST /threads/search` with `{}` body (backend injects owner filter) |
| `POST /api/v1/threads` | `POST /threads` |
| `DELETE /api/v1/threads/{id}` | `DELETE /threads/{id}` |
| `GET /api/v1/threads/{id}/history` | **Removed** — `useStream()` handles history |

### `lib/hooks/useThreads.ts`

Remove `useThreadHistory` hook entirely.

### `components/chat/ChatView.tsx`

Remove `useThreadHistory` import and usage. The `useStream()` hook automatically loads prior messages when given an existing `threadId`.

### Schema mapping

Aegra threads return metadata as a nested object. Update all consumer code:

| Before | After |
|--------|-------|
| `thread.assistant_id` | `thread.metadata?.assistant_id` |
| `thread.thread_name` | `thread.metadata?.thread_name` |
| `thread.owner` | `thread.metadata?.owner` |

---

## Aegra Native Endpoints (reference)

### Assistants
| Method | Path |
|--------|------|
| `POST` | `/assistants` |
| `GET` | `/assistants` |
| `GET` | `/assistants/{id}` |
| `PATCH` | `/assistants/{id}` |
| `DELETE` | `/assistants/{id}` |

### Threads
| Method | Path |
|--------|------|
| `POST` | `/threads` |
| `POST` | `/threads/search` |
| `GET` | `/threads/{id}` |
| `DELETE` | `/threads/{id}` |
| `POST` | `/threads/{id}/runs/stream` ← already used by `useStream()` |
| `POST` | `/threads/{id}/runs/wait` |
| `GET` | `/threads/{id}/state` |
| `GET` | `/threads/{id}/history` |

---

## What Stays

- `src/api/routes/auth.py` — login, register, refresh, me
- `src/api/routes/users.py` — user CRUD + admin actions
- `src/services/` auth and user services
- `src/models/user.py`
- `src/schemas/` auth and user schemas
- `src/auth/jwt.py` — extended with `@auth.on` handlers
