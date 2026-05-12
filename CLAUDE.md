# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Full-stack LangGraph agent template: FastAPI + [Aegra](https://github.com/aegra-dev/aegra) backend serving both custom REST endpoints and the LangGraph API, with a Next.js 16 frontend. The backend runs on port **2026**; the frontend on port **3000**.

## Commands

### Backend (run from `backend/`)

```bash
# Install dependencies
uv sync

# Start dev server (auto-starts PostgreSQL via Docker, runs migrations)
uv run aegra dev

# Lint + type-check
task lint          # ruff check && mypy .
task format        # ruff format

# Tests (runs lint first, then coverage report)
task test

# Single test file
uv run pytest tests/test_auth_service.py -s -x -vv

# Database migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"

# Reset DB
docker compose down -v && docker compose up postgres -d && uv run alembic upgrade head
```

### Frontend (run from `frontend/`)

```bash
npm run dev        # Next.js dev server on :3000
npm run build
npm test           # vitest (watch mode)
npm run test:run   # vitest (single run)
```

## Architecture

### Request Flow

All traffic flows through a single Aegra server on port 2026:
- `/api/v1/*` → custom FastAPI routes (auth, user CRUD)
- `/threads`, `/runs`, `/assistants` → Aegra's LangGraph API (proxied directly)

The frontend's `apiClient` (`frontend/lib/api/client.ts`) sends all requests to `NEXT_PUBLIC_API_URL` (default: `http://localhost:2024`). Route protection is done in `frontend/proxy.ts` (Next.js middleware) by checking the `access_token` cookie.

### Auth Architecture

JWT-based dual-layer auth:
1. **FastAPI layer** (`src/core/security.py`): `get_current_user` dependency validates Bearer tokens for `/api/v1/*` routes.
2. **Aegra/LangGraph layer** (`src/auth/jwt.py`): `@auth.authenticate` handler validates the same tokens before every LangGraph endpoint call. Registered in `aegra.json`.

Token storage: access token in Zustand store + non-HttpOnly cookie (for middleware); refresh token in `localStorage`. Token refresh is deduplicated via a shared promise in `apiClient`.

**Admin promotion is manual**: `POST /api/v1/auth/register` always creates `is_admin=false`. Promote via SQL:
```bash
docker exec -it backend-postgres psql -U backend -d backend \
  -c "UPDATE users SET is_admin = true WHERE email = 'you@example.com';"
```

### Agent / LangGraph Architecture

The agent is a LangGraph ReAct graph defined in `src/agent/graph.py`, registered as `"agent"` in `aegra.json`. Key pieces:

- **`Context`** (`src/agent/context.py`): dataclass injected at runtime; holds `model` and `system_prompt`. Overridable per-assistant via `config.configurable` when creating an assistant, or globally via `MODEL`/`SYSTEM_PROMPT` env vars.
- **`dynamic_system_prompt`**: middleware that reads `system_prompt` from the runtime context and injects the current UTC time.
- **`TOOLS`** (`src/agent/tools.py`): list of LangChain tools passed to the agent. Add new tools here.
- **`load_chat_model`** (`src/agent/utils.py`): resolves `"provider/model"` strings to LangChain chat models. Supports `anthropic/`, `openai/`, `ollama/` prefixes.

### Thread / Assistant Quirk

Aegra reserves the `assistant_id` field in thread metadata. The frontend stores the assistant association as `thread_assistant_id` in metadata instead (see `frontend/lib/api/threads.ts`).

### Frontend Structure

- **Route groups**: `(auth)` for login/signup, `(app)/(picker)` for the assistant selection screen, `(app)/(chat)` for the chat interface + admin.
- **State**: Zustand for auth (`lib/store/auth.ts`), TanStack Query for server state (assistants, threads, users).
- **API layer**: `lib/api/` modules wrap `apiClient` with typed functions (`lib/api/client.ts`). All LangGraph streaming calls use `@langchain/langgraph-sdk` directly in chat components.
- **UI**: shadcn/ui components (Base UI primitives) + Tailwind CSS v4.

### Database

PostgreSQL via SQLAlchemy async (asyncpg driver). Alembic migrations in `backend/migrations/versions/`. The `settings.db_url` computed field builds the asyncpg connection string from individual env vars or falls back to `DATABASE_URL`.

## Key Configuration Files

- `backend/aegra.json` — registers the FastAPI app, LangGraph graphs, CORS, and the JWT auth handler
- `backend/.env` — copy from `.env.example`; mandatory: `JWT_SECRET_KEY` (≥32 chars), at least one LLM API key
- `frontend/.env.example` — copy to `.env.local`; set `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:2026`)

## Next.js Version Note

This project uses **Next.js 16.2.1** with React 19. APIs and conventions may differ from training data. Read `node_modules/next/dist/docs/` before writing Next.js-specific code.
