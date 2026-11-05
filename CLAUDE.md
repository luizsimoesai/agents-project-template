# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Full-stack LangGraph agent template: FastAPI + [Aegra](https://github.com/aegra-dev/aegra) backend serving both custom REST endpoints and the LangGraph API, with a Vite + React Router SPA frontend. The backend runs on port **2026**; the frontend on port **3000**.

## Commands

### Backend (run from `backend/`)

```bash
# Install dependencies
uv sync

# Start dev server (auto-starts PostgreSQL via Docker, runs Aegra's own migrations)
uv run aegra dev

# Lint + type-check
task lint          # ruff check && mypy .
task format        # ruff format

# Tests (runs lint first, then coverage report)
task test

# Single test file
uv run pytest tests/test_auth_service.py -s -x -vv

# Database migrations (this project's chain only — users/llm_models; Aegra runs its own on startup)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
uv run alembic heads   # check for multiple heads (parallel branches)

# Reset DB
docker compose down -v && docker compose up postgres -d && uv run alembic upgrade head
```

### Frontend (run from `frontend/`)

```bash
npm run dev        # Vite dev server on :3000
npm run build      # type-check + static build to dist/
npm run preview    # serve dist/ on :3000
npm test           # vitest (watch mode)
npm run test:run   # vitest (single run)
```

## Architecture

### Request Flow

All traffic flows through a single Aegra server on port 2026:
- `/api/v1/*` → custom FastAPI routes (auth, user CRUD, model catalog)
- `/threads`, `/runs`, `/assistants` → Aegra's LangGraph API (proxied directly)

The frontend's `apiClient` (`frontend/src/lib/api/client.ts`) sends every request with `credentials: "include"` to `VITE_API_URL` (default: `http://localhost:2026`). Route protection is client-side: `RequireAuth` and `RequireGuest` (`frontend/src/components/auth/RouteGuards.tsx`) gate on the in-memory access token.

### Auth Architecture

JWT-based dual-layer auth:
1. **FastAPI layer** (`src/core/security.py`): `get_current_user` dependency validates Bearer tokens for `/api/v1/*` routes. `get_current_admin` extends it with an `is_admin` check.
2. **Aegra/LangGraph layer** (`src/auth/jwt.py`): `@auth.authenticate` validates the same tokens AND re-checks the user exists and `is_active` against the DB on every call. Admins receive `permissions: ["admin", "authenticated"]`.

**Token storage**
- **Access token**: returned in the `/auth/login` response body and held only in memory, in Zustand (`src/lib/store/auth.ts`). It is never written to a cookie or to browser storage.
- **Refresh token**: set by the server as an `HttpOnly; Secure; SameSite=Lax` cookie scoped to `Path=/api/v1/auth`. JS never reads it. The browser includes it automatically on `/auth/refresh` and `/auth/logout` because every fetch sends `credentials: "include"`.
- **Session restore**: on load, `AuthProvider` calls `/auth/refresh` once and renders a loading state until it settles, so no route or guard runs before the session is known.

**Refresh-token rotation with replay detection**: every refresh JWT carries a `jti` claim that must match `users.refresh_jti`. On each `/auth/refresh` the server rotates `refresh_jti`; presenting a stale `jti` (replay / theft) is rejected AND the stored `jti` is cleared, forcing even the legitimate session to re-login.

**Refresh single-flight**: `tryRefresh()` in `client.ts` dedupes concurrent 401s via a module-level promise. `apiClient` also short-circuits — if the store token already differs from the one we sent, it retries with the new token without calling `/refresh` at all.

**Rate limiting** (`src/core/rate_limit.py` via [slowapi](https://github.com/laurents/slowapi)): `/auth/login` 5/min, `/auth/register` 3/min, `/auth/refresh` 10/min, keyed by IP. In-memory backend — for multi-instance deployments configure a Redis storage URI. Disabled in tests via `RATE_LIMIT_ENABLED=false` (set in `conftest.py`).

**Admin promotion is manual**: `POST /api/v1/auth/register` always creates `is_admin=false`. Promote via SQL:
```bash
docker exec -it backend-postgres psql -U backend -d backend \
  -c "UPDATE users SET is_admin = true WHERE email = 'you@example.com';"
```

`POST /api/v1/users` exists but requires admin (use `/auth/register` for public signup).

### Agent / LangGraph Architecture

Two graphs are registered in `aegra.json`:
- **`basic_agent`** (`src/agent/basic_agent/graph.py`): plain `create_agent` ReAct loop with the tools in `src/agent/basic_agent/tools.py`.
- **`deep_agent`** (`src/agent/deep_agent/graph.py`): `create_deep_agent` with planning + sub-agent tools (`src/agent/deep_agent/tools.py`).

Shared runtime model selection (`src/agent/model.py`):
- **`Context`** dataclass — injected at runtime; holds `model` (e.g. `"anthropic:claude-sonnet-4-6"` or `"ollama/llama3:8b"`) and optional `model_base_url`. Defaults read from `MODEL` / `MODEL_BASE_URL` env vars. Override per-assistant via `config.configurable`.
- **`configurable_model`** — `@wrap_model_call` middleware (async only). It pulls `model`/`model_base_url` from `runtime.context`, builds (or fetches from `lru_cache`) the `BaseChatModel`, and `request.override(model=...)` swaps it in. Both graphs pass `middleware=[configurable_model]`, so the static `model=` argument is effectively a placeholder — the middleware is the source of truth.
- **`_split_provider`** — parses both `provider/model` and `provider:model` (first separator wins; `ollama/llama3:8b` keeps `:8b` as part of the model name).
- **`_load`** — caches `init_chat_model(...)` results (`lru_cache(maxsize=32)`).

Tool docstrings ARE the prompt the LLM sees — keep them descriptive (inputs, outputs, error formats).

### Thread / Assistant Quirk

Aegra overwrites the `assistant_id` field in thread metadata after each run (tracks last-used). To pin a thread to its original assistant the frontend stores `thread_assistant_id` in metadata instead — see `frontend/src/lib/api/threads.ts` and `frontend/src/lib/hooks/useThreads.ts`.

Aegra authorization (`src/auth/jwt.py`) scopes every thread/assistant operation to `metadata.owner == ctx.user.identity`. Filter handlers are installed for `read`, `update`, `delete`, `search`, and `create_run` on both resources. Without these, any authenticated user could list everyone's threads.

### Frontend Structure

- **Routes**: the tree lives in `src/router.tsx` (React Router data mode); pages and layouts live in `src/routes/`. `AuthLayout` wraps login/signup, `PickerLayout` the assistant selection screen, `ChatLayout` the chat interface, profile and admin.
- **State**: Zustand for auth (`src/lib/store/auth.ts`), TanStack Query for server state (assistants, threads, users, models).
- **API layer**: `src/lib/api/` modules wrap `apiClient` from `src/lib/api/client.ts`. `apiClient` automatically attaches the Bearer token, sends `credentials: "include"`, and handles 401 → refresh → retry. On refresh failure it throws `ApiAuthError` and navigates to `/login`.
- **Logout**: `src/lib/api/auth.ts` `logout()` calls `POST /auth/logout` (invalidates `refresh_jti` + clears the cookie) then `clearAuth()`.
- **Streaming**: chat components use `useStream` from `@langchain/langgraph-sdk/react` directly. `apiUrl` is imported from `src/lib/api/client.ts` so it stays aligned with REST calls.
- **UI**: shadcn/ui components (Base UI primitives) + Tailwind CSS v4.

### Database

PostgreSQL via SQLAlchemy async (asyncpg driver). Alembic migrations in `backend/migrations/versions/`. Current chain: `95ddd19a5855` → `b3e9f1a2c4d5` → `3189b185e75b` → `c4f7d2a8e1b3`. The `settings.db_url` computed field builds the asyncpg connection string from individual env vars or falls back to `DATABASE_URL`.

**Two independent migration chains share the database.** Aegra (≥0.9.20) runs its *own* bundled migrations on server startup, tracked in the default `alembic_version` table, creating the LangGraph tables (threads, runs, assistants, checkpoints, …). This project's migrations are a *separate* chain — run via `uv run alembic upgrade head` (or `task bootstrap`), tracked in a dedicated `alembic_version_app` table (set via `version_table` in `migrations/env.py`), creating only `users` / `llm_models`. The separate version table is required: sharing the default makes whichever chain runs second abort with `Can't locate revision`. `include_object` in `env.py` keeps the project chain from touching Aegra-owned tables. Consequence: `aegra dev` alone does **not** create the project tables — run `alembic upgrade head` too. (Before Aegra 0.9.20, the buggy `find_alembic_ini` made Aegra run the *project's* alembic.ini at startup, which masked this; a now-removed `_ensure_aegra_tables()` workaround in `env.py` create_all'd the Aegra tables.)

When adding a migration, set `down_revision` to the current `alembic heads` output — otherwise you create a parallel branch in this project's chain and `alembic upgrade head` (and `task bootstrap`) fails with `MultipleHeads`. UUID primary keys default to `gen_random_uuid()` (Postgres 13+ core) — no `uuid-ossp` extension required.

## Key Configuration Files

- `backend/aegra.json` — registers the FastAPI app, LangGraph graphs, CORS, and the JWT auth handler. CORS allows `http://localhost:3000` with `allow_credentials: true` (required for the HttpOnly cookie flow).
- `backend/.env` — copy from `.env.example`. **Required** (no defaults — `Settings()` refuses to boot without these): `JWT_SECRET_KEY` (≥32 chars, generate with `openssl rand -hex 32`), `POSTGRES_PASSWORD`, at least one LLM API key. Set `COOKIE_SECURE=false` for HTTP dev.
- `frontend/.env.example` — copy to `.env.local`; set `VITE_API_URL` (defaults to `http://localhost:2026`).
- `backend/pyproject.toml` — ruff strict (`I, F, E, W, PL, PT, FAST`), mypy strict, taskipy tasks. Tests are excluded from mypy via `[[tool.mypy.overrides]]`.

## Testing notes

- `backend/tests/conftest.py` force-sets `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, and `RATE_LIMIT_ENABLED=false` at the top of the file (before imports that trigger `Settings()`) so tests are hermetic.
- DB-touching unit tests use `AsyncMock(spec=AsyncSession)` and the `_make_execute_result` helper for `scalar_one_or_none` returns. See `tests/test_auth_service.py` for the pattern.
- Aegra auth handler tests (`tests/test_auth_handler.py`) mock `src.auth.jwt._fetch_active_user` since the real function requires a live Aegra DB.
- Frontend tests use Vitest (`npm run test:run`). The client-refresh tests mock `fetch` and `localStorage`; pay attention to module-level state (`refreshPromise` in `client.ts`) when adding tests.

## Frontend Routing Notes

- `ChatLayout` keys `<main>` by pathname so pages remount when a route param changes. `ChatView` keeps per-thread state in refs and depends on this. Query-string changes must not remount it: removing `?msg=` happens while the first message is streaming.
- Render at most one `<title>` at a time. React inserts it before the default title from `index.html`, so nested titles conflict. `ChatLayout` owns the dynamic ones.
- The `*` route sits inside `RequireAuth`: unknown URLs send guests to `/login`, not to the 404 page.
- React Compiler runs through `@rolldown/plugin-babel` in `vite.config.ts`, because `@vitejs/plugin-react` 6 has no `babel` option.
