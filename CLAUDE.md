# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangGraph-based AI agent backend using the [Aegra](https://aegra.dev) framework. The agent follows a **ReAct (Reasoning + Acting)** pattern, deployed as both a LangGraph graph endpoint and a FastAPI HTTP server. All backend code lives in the `backend/` directory.

## Commands

All commands should be run from the `backend/` directory.

```bash
# Install dependencies (uses uv)
uv sync

# Development server (starts Aegra with hot reload + DB setup)
task run          # equivalent to: uv run aegra dev

# Linting and type checking
task lint         # ruff check + mypy

# Code formatting
task format       # ruff format

# Tests (runs lint first, then pytest with coverage)
task test

# Run a single test file
uv run pytest tests/path/to/test_file.py -s -x -vv
```

**Docker (full stack):**
```bash
docker-compose up --build    # PostgreSQL + API
docker-compose up postgres   # Database only
```

**Database migrations (Alembic):**
```bash
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Architecture

### Aegra Framework
Aegra (`aegra.json`) is the deployment harness. It registers:
- The **agent graph** at `src/agent/graph.py:graph` — exposed as a LangGraph API
- The **HTTP app** at `src/main.py:app` — exposed as a FastAPI server

### Agent Graph (`src/agent/`)
The ReAct agent loop:
1. `call_model` — invokes the LLM with bound tools and system prompt
2. `route_model_output` — branches to `tools` node or `END` based on whether tool calls exist
3. `tools` (ToolNode) — executes requested tools, loops back to `call_model`

Key files:
- `graph.py` — StateGraph definition and compilation
- `state.py` — `InputState` (messages) and `State` (adds `is_last_step`)
- `context.py` — Runtime config dataclass: `model` and `system_prompt`, overridable via env vars `MODEL` / `SYSTEM_PROMPT`
- `tools.py` — Add LangChain `@tool`-decorated functions here
- `prompts.py` — System prompt template (receives `{system_time}` at runtime)
- `utils.py` — `load_chat_model("provider/model-name")` helper

### Model Loading
Models are specified as `"provider/model"` strings (e.g., `"openai/gpt-4o-mini"`, `"anthropic/claude-sonnet-4-6"`). The default is `"ollama/gpt-oss:120b-cloud"`. Override via the `MODEL` env var or per-request context.

### Database
PostgreSQL with SQLAlchemy ORM + Alembic migrations. Models live in `src/models/`. The `User` model (`src/models/user.py`) is the only seeded model — uses UUID primary keys and automatic timestamps.

### Environment
Copy `.env.example` to `.env`. Key variables:
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` — LLM provider keys
- `DATABASE_URL` or individual `DB_*` vars — PostgreSQL connection
- `MODEL`, `SYSTEM_PROMPT` — override agent defaults
- `ENV_MODE` — `LOCAL` | `DEVELOPMENT` | `PRODUCTION`
- `AUTH_TYPE` — `noop` (default, no auth) or custom
