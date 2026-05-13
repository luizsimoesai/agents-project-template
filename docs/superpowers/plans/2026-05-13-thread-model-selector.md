# Thread Model Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to choose which LLM model to use per conversation thread, persisted in thread metadata, managed by admins via a model catalog.

**Architecture:** A `DynamicModel` proxy (`BaseChatModel` subclass) reads `model` and `model_base_url` from `config.configurable` at call time, making all graphs model-agnostic. Admins manage the catalog via a new `llm_models` DB table + REST API. The frontend stores the selection in thread metadata and passes it as configurable on every submit.

**Tech Stack:** Python/FastAPI/SQLAlchemy/Alembic (backend), Next.js 16/React 19/TanStack Query/shadcn-style @base-ui/react components (frontend), LangChain/LangGraph/Aegra, PostgreSQL.

---

## File Map

**Backend — create:**
- `backend/src/models/llm_model.py` — SQLAlchemy ORM model for `llm_models` table
- `backend/src/schemas/llm_model.py` — Pydantic ModelRead / ModelCreate / ModelUpdate
- `backend/src/services/model_service.py` — CRUD + set_default logic
- `backend/src/api/routes/models.py` — FastAPI router
- `backend/tests/test_dynamic_model.py` — DynamicModel unit tests
- `backend/tests/test_model_service.py` — ModelService unit tests
- `backend/tests/test_routes_models.py` — route integration tests

**Backend — modify:**
- `backend/src/agent/utils.py` — add `base_url` param, `_cached_load`, `DynamicModel`, `DYNAMIC_MODEL`
- `backend/src/agent/context.py` — add `model_base_url` field
- `backend/src/agent/graph.py` — replace module-level `_model` with `DYNAMIC_MODEL`
- `backend/src/agent/deepagents/graph.py` — same
- `backend/src/models/__init__.py` — export `LLMModel`
- `backend/migrations/env.py` — import `LLMModel` to register in metadata
- `backend/src/main.py` — register models router
- `backend/tests/conftest.py` — add `model_factory` fixture

**Frontend — create:**
- `frontend/components/ui/select.tsx` — @base-ui/react/select wrapper
- `frontend/components/ui/tabs.tsx` — @base-ui/react/tabs wrapper
- `frontend/lib/api/models.ts` — typed API functions
- `frontend/lib/hooks/useModels.ts` — TanStack Query hooks
- `frontend/components/admin/AdminModelTable.tsx`
- `frontend/components/admin/ModelForm.tsx`

**Frontend — modify:**
- `frontend/lib/types.ts` — add ModelRead/Create/Update, update ThreadRead.metadata
- `frontend/lib/hooks/useThreads.ts` — add `useThread` + `useUpdateThreadModel`
- `frontend/app/(app)/(chat)/admin/page.tsx` — tabbed Users | Modelos
- `frontend/components/assistants/AssistantForm.tsx` — remove model field
- `frontend/components/chat/ChatView.tsx` — add model selector

---

## Task 1: DynamicModel proxy + graph updates

**Files:**
- Modify: `backend/src/agent/utils.py`
- Modify: `backend/src/agent/context.py`
- Modify: `backend/src/agent/graph.py`
- Modify: `backend/src/agent/deepagents/graph.py`
- Create: `backend/tests/test_dynamic_model.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_dynamic_model.py`:

```python
import os
from unittest.mock import MagicMock, patch

import pytest

from src.agent.utils import DynamicModel, load_chat_model


# ── load_chat_model ───────────────────────────────────────────────────────────


def test_load_chat_model_passes_base_url():
    with patch("src.agent.utils.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock()
        load_chat_model("openai/gpt-4o", base_url="https://proxy.example.com")
        mock_init.assert_called_once_with(
            "gpt-4o", model_provider="openai", base_url="https://proxy.example.com"
        )


def test_load_chat_model_no_base_url_omits_kwarg():
    with patch("src.agent.utils.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock()
        load_chat_model("openai/gpt-4o")
        mock_init.assert_called_once_with("gpt-4o", model_provider="openai")


# ── DynamicModel._resolve ─────────────────────────────────────────────────────


def test_resolve_reads_model_id_from_configurable():
    with patch("src.agent.utils._cached_load") as mock_load:
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        proxy = DynamicModel()
        config = {"configurable": {"model": "anthropic/claude-sonnet-4-6", "model_base_url": None}}
        result = proxy._resolve(config)

        mock_load.assert_called_once_with("anthropic/claude-sonnet-4-6", None)
        assert result is mock_model


def test_resolve_reads_base_url_from_configurable():
    with patch("src.agent.utils._cached_load") as mock_load:
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        proxy = DynamicModel()
        config = {
            "configurable": {
                "model": "ollama/llama3",
                "model_base_url": "http://localhost:11434",
            }
        }
        proxy._resolve(config)

        mock_load.assert_called_once_with("ollama/llama3", "http://localhost:11434")


def test_resolve_falls_back_to_env_var(monkeypatch):
    monkeypatch.setenv("MODEL", "openai/gpt-4o-mini")
    with patch("src.agent.utils._cached_load") as mock_load:
        mock_load.return_value = MagicMock()
        proxy = DynamicModel()
        proxy._resolve({})
        mock_load.assert_called_once_with("openai/gpt-4o-mini", None)


def test_resolve_none_config_falls_back_to_env_var(monkeypatch):
    monkeypatch.setenv("MODEL", "openai/gpt-4o-mini")
    with patch("src.agent.utils._cached_load") as mock_load:
        mock_load.return_value = MagicMock()
        proxy = DynamicModel()
        proxy._resolve(None)
        mock_load.assert_called_once_with("openai/gpt-4o-mini", None)


# ── DynamicModel.bind_tools ───────────────────────────────────────────────────


def test_bind_tools_returns_new_proxy_with_tools():
    tool_a = MagicMock()
    tool_b = MagicMock()

    proxy = DynamicModel()
    bound = proxy.bind_tools([tool_a, tool_b])

    assert isinstance(bound, DynamicModel)
    assert bound is not proxy
    assert bound.bound_tools == [tool_a, tool_b]


def test_bind_tools_passes_kwargs():
    proxy = DynamicModel()
    bound = proxy.bind_tools([], tool_choice="any")
    assert bound.bound_kwargs == {"tool_choice": "any"}


def test_resolve_binds_tools_to_real_model():
    with patch("src.agent.utils._cached_load") as mock_load:
        real_model = MagicMock()
        bound_model = MagicMock()
        real_model.bind_tools.return_value = bound_model
        mock_load.return_value = real_model

        tool = MagicMock()
        proxy = DynamicModel(bound_tools=[tool])
        config = {"configurable": {"model": "openai/gpt-4o"}}
        result = proxy._resolve(config)

        real_model.bind_tools.assert_called_once_with([tool])
        assert result is bound_model


# ── DynamicModel.invoke ───────────────────────────────────────────────────────


def test_invoke_delegates_to_resolved_model():
    with patch("src.agent.utils._cached_load") as mock_load:
        real_model = MagicMock()
        mock_load.return_value = real_model
        real_model.invoke.return_value = MagicMock()

        proxy = DynamicModel()
        config = {"configurable": {"model": "openai/gpt-4o"}}
        messages = [MagicMock()]
        proxy.invoke(messages, config)

        real_model.invoke.assert_called_once_with(messages, config)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_dynamic_model.py -x -vv
```

Expected: `ImportError` or `AttributeError` — `DynamicModel` does not exist yet.

- [ ] **Step 3: Implement `load_chat_model` extension + `DynamicModel`**

Replace the entire content of `backend/src/agent/utils.py`:

```python
"""Utility functions and graph-agnostic model proxy for the backend."""

from __future__ import annotations

import functools
import os
from typing import Any, Iterator, AsyncIterator

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable
from pydantic import Field

_DEFAULT_MODEL = "ollama/gpt-oss:120b-cloud"


def load_chat_model(
    fully_specified_name: str,
    *,
    base_url: str | None = None,
) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name: 'provider/model' format,
            e.g. 'openai/gpt-4o-mini', 'anthropic/claude-sonnet-4-6'.
        base_url: Optional base URL for Ollama or proxy servers.

    Returns:
        A BaseChatModel instance.
    """
    if not fully_specified_name or not fully_specified_name.strip():
        raise ValueError(
            "fully_specified_name must be in 'provider/model' format, got empty string"
        )
    if fully_specified_name.count("/") != 1:
        raise ValueError(
            f"fully_specified_name must be in 'provider/model' format, "
            f"got '{fully_specified_name}'"
        )
    provider, model = fully_specified_name.split("/", maxsplit=1)
    if not provider.strip() or not model.strip():
        raise ValueError(
            f"fully_specified_name must be in 'provider/model' format, "
            f"got '{fully_specified_name}'"
        )
    kwargs: dict[str, str] = {}
    if base_url:
        kwargs["base_url"] = base_url
    return init_chat_model(model, model_provider=provider, **kwargs)


@functools.lru_cache(maxsize=32)
def _cached_load(model_id: str, base_url: str | None) -> BaseChatModel:
    """Load and cache a BaseChatModel by (model_id, base_url) key."""
    return load_chat_model(model_id, base_url=base_url)


class DynamicModel(BaseChatModel):
    """Graph-agnostic model proxy.

    Reads `model` and `model_base_url` from config.configurable at call time,
    so any graph using DYNAMIC_MODEL automatically supports per-thread model
    selection without any graph-specific changes.
    """

    bound_tools: list[Any] = Field(default_factory=list)
    bound_kwargs: dict[str, Any] = Field(default_factory=dict)

    @property
    def _llm_type(self) -> str:
        return "dynamic"

    def _resolve(self, config: dict[str, Any] | None) -> Runnable:
        cfg = (config or {}).get("configurable", {}) if config else {}
        model_id: str = cfg.get("model") or os.environ.get("MODEL", _DEFAULT_MODEL)
        base_url: str | None = cfg.get("model_base_url") or None
        real: BaseChatModel = _cached_load(model_id, base_url)
        if self.bound_tools:
            return real.bind_tools(self.bound_tools, **self.bound_kwargs)
        return real

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "DynamicModel":
        return DynamicModel(bound_tools=list(tools), bound_kwargs=dict(kwargs))

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Never called directly — invoke/stream delegate to the resolved model.
        raise NotImplementedError("Use invoke/ainvoke/stream/astream")

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return self._resolve(config).invoke(input, config, **kwargs)

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        return await self._resolve(config).ainvoke(input, config, **kwargs)

    def stream(self, input: Any, config: Any = None, **kwargs: Any) -> Iterator[Any]:
        return self._resolve(config).stream(input, config, **kwargs)

    async def astream(
        self, input: Any, config: Any = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        async for chunk in self._resolve(config).astream(input, config, **kwargs):
            yield chunk


DYNAMIC_MODEL = DynamicModel()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_dynamic_model.py -x -vv
```

Expected: all tests PASS.

- [ ] **Step 5: Add `model_base_url` to Context**

Edit `backend/src/agent/context.py` — add the `model_base_url` field after `model`:

```python
    model: Annotated[str, {"description": "LLM model as 'provider/model'."}] = field(
        default="ollama/gpt-oss:120b-cloud",
    )
    model_base_url: Annotated[
        str | None, {"description": "Optional base URL for Ollama or proxy servers."}
    ] = field(default=None)
```

Also update `__post_init__` to handle the env override (add after the `env_prompt` block):

```python
        env_base_url = os.environ.get("MODEL_BASE_URL")
        if env_base_url:
            self.model_base_url = env_base_url
```

- [ ] **Step 6: Update `agent/graph.py` to use DYNAMIC_MODEL**

Replace the module-level `_model` line and its usage in `create_agent`:

```python
"""ReAct agent with dynamic system prompt."""

from datetime import UTC, datetime

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt

from agent.context import Context
from agent.tools import TOOLS
from agent.utils import DYNAMIC_MODEL


@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    context: Context = request.runtime.context or Context()
    return str(
        context.system_prompt.format(system_time=datetime.now(tz=UTC).isoformat())
    )


graph = create_agent(
    model=DYNAMIC_MODEL,
    tools=TOOLS,
    context_schema=Context,
    middleware=[
        dynamic_system_prompt,
    ],
    name="agent",
)
```

- [ ] **Step 7: Update `deepagents/graph.py` to use DYNAMIC_MODEL**

Replace the entire file:

```python
"""DeepAgent example using the deepagents quickstart pattern."""

from deepagents import create_deep_agent

from agent.deepagents.tools import TOOLS
from agent.utils import DYNAMIC_MODEL

_SYSTEM_PROMPT = """You are a helpful assistant with planning and tool-use capabilities.

You have access to tools to help answer questions:
- `get_current_time`: returns the current UTC time
- `calculator`: evaluates arithmetic expressions

Break complex tasks into steps using your built-in planning tools, then execute them."""

graph = create_deep_agent(
    model=DYNAMIC_MODEL,
    tools=TOOLS,
    system_prompt=_SYSTEM_PROMPT,
    name="deep_agent",
)
```

- [ ] **Step 8: Commit**

```bash
cd backend
git add src/agent/utils.py src/agent/context.py src/agent/graph.py src/agent/deepagents/graph.py tests/test_dynamic_model.py
git commit -m "feat: add DynamicModel proxy for graph-agnostic model selection"
```

---

## Task 2: LLMModel database model + Alembic migration

**Files:**
- Create: `backend/src/models/llm_model.py`
- Modify: `backend/src/models/__init__.py`
- Modify: `backend/migrations/env.py`

- [ ] **Step 1: Create `backend/src/models/llm_model.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.user import table_registry


@table_registry.mapped_as_dataclass
class LLMModel:
    __tablename__ = "llm_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        init=False,
        primary_key=True,
        default_factory=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    base_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 2: Update `backend/src/models/__init__.py`**

```python
from src.models.llm_model import LLMModel
from src.models.user import User

__all__ = ["LLMModel", "User"]
```

- [ ] **Step 3: Update `backend/migrations/env.py` to register LLMModel**

Add one import after the `from src.models.user import table_registry` line:

```python
from src.models.user import table_registry
from src.models.llm_model import LLMModel as _LLMModel  # noqa: F401 — registers table in metadata
```

- [ ] **Step 4: Generate and verify the migration**

```bash
cd backend && uv run alembic revision --autogenerate -m "add llm_models table"
```

Open the generated file in `backend/migrations/versions/`. Verify it contains:
- `op.create_table("llm_models", ...)` with all columns
- No unexpected `op.drop_table` statements

- [ ] **Step 5: Apply the migration**

```bash
cd backend && uv run alembic upgrade head
```

Expected: completes without error.

- [ ] **Step 6: Commit**

```bash
cd backend
git add src/models/llm_model.py src/models/__init__.py migrations/env.py migrations/versions/
git commit -m "feat: add llm_models table and Alembic migration"
```

---

## Task 3: ModelService + schemas

**Files:**
- Create: `backend/src/schemas/llm_model.py`
- Create: `backend/src/services/model_service.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_model_service.py`

- [ ] **Step 1: Write the failing tests**

First add the `model_factory` fixture to `backend/tests/conftest.py` — append after the `make_token` fixture:

```python
@pytest.fixture
def model_factory():
    """Factory that creates LLMModel ORM instances for tests."""

    def make(**kwargs: Any) -> "LLMModel":
        from src.models.llm_model import LLMModel

        defaults: dict[str, Any] = {
            "display_name": "Test Model",
            "model_id": "openai/gpt-4o",
            "provider": "openai",
            "description": None,
            "base_url": None,
            "is_active": True,
            "is_default": False,
        }
        defaults.update(kwargs)
        m = LLMModel(  # type: ignore[call-arg]
            display_name=defaults["display_name"],
            model_id=defaults["model_id"],
            provider=defaults["provider"],
            description=defaults["description"],
            base_url=defaults["base_url"],
            is_active=defaults["is_active"],
            is_default=defaults["is_default"],
        )
        if not getattr(m, "id", None):
            m.id = uuid.uuid4()
        m.created_at = defaults.get("created_at", datetime.now(timezone.utc))
        m.updated_at = defaults.get("updated_at", datetime.now(timezone.utc))
        return m

    return make
```

Also add `from datetime import datetime, timezone` to the imports at the top of `conftest.py` (it is already there — no change needed).

Now create `backend/tests/test_model_service.py`:

```python
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.schemas.llm_model import ModelCreate, ModelUpdate
from src.services.model_service import ModelService


def _make_refresh_side_effect(mock_session: AsyncMock) -> None:
    async def do_refresh(obj):
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime.now(timezone.utc)

    mock_session.refresh.side_effect = do_refresh


def _make_execute_result(rows: list) -> MagicMock:
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    result.scalars.return_value = scalars_mock
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    return result


# ── create_model ──────────────────────────────────────────────────────────────


async def test_create_model_success(mock_session, model_factory):
    _make_refresh_side_effect(mock_session)
    # execute for set_default (UPDATE) returns no rows — use a plain MagicMock
    mock_session.execute.return_value = MagicMock()
    service = ModelService(mock_session)

    data = ModelCreate(
        display_name="GPT-4o",
        model_id="openai/gpt-4o",
        provider="openai",
    )
    result = await service.create_model(data)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited()
    assert result.display_name == "GPT-4o"
    assert result.model_id == "openai/gpt-4o"


async def test_create_model_with_is_default_calls_set_default(mock_session, model_factory):
    m = model_factory(model_id="openai/gpt-4o", is_active=True)
    _make_refresh_side_effect(mock_session)
    # First execute: set_default UPDATE; second execute: _fetch_model for get_model
    mock_session.execute.side_effect = [
        MagicMock(),  # UPDATE is_default=False
        MagicMock(),  # UPDATE is_default=True
        _make_execute_result([m]),  # SELECT for get_model
    ]
    service = ModelService(mock_session)

    data = ModelCreate(
        display_name="GPT-4o",
        model_id="openai/gpt-4o",
        provider="openai",
        is_default=True,
    )
    result = await service.create_model(data)

    assert result.is_default is True
    # set_default triggers at least 2 execute calls (zero all, set one)
    assert mock_session.execute.await_count >= 2


# ── get_model ─────────────────────────────────────────────────────────────────


async def test_get_model_found(mock_session, model_factory):
    m = model_factory(display_name="Claude", model_id="anthropic/claude-sonnet-4-6")
    mock_session.execute.return_value = _make_execute_result([m])
    service = ModelService(mock_session)

    result = await service.get_model(m.id)

    assert result.display_name == "Claude"
    assert result.model_id == "anthropic/claude-sonnet-4-6"


async def test_get_model_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _make_execute_result([])
    service = ModelService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_model(uuid.uuid4())

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ── list_models ───────────────────────────────────────────────────────────────


async def test_list_active_models_excludes_inactive(mock_session, model_factory):
    active = model_factory(model_id="openai/gpt-4o", is_active=True)
    mock_session.execute.return_value = _make_execute_result([active])
    service = ModelService(mock_session)

    result = await service.list_active_models()

    assert len(result) == 1
    assert result[0].model_id == "openai/gpt-4o"


async def test_list_all_models_returns_all(mock_session, model_factory):
    models = [
        model_factory(model_id="openai/gpt-4o", is_active=True),
        model_factory(model_id="openai/gpt-3.5-turbo", is_active=False),
    ]
    mock_session.execute.return_value = _make_execute_result(models)
    service = ModelService(mock_session)

    result = await service.list_all_models()

    assert len(result) == 2


# ── update_model ──────────────────────────────────────────────────────────────


async def test_update_model_display_name(mock_session, model_factory):
    m = model_factory(display_name="Old Name")
    mock_session.execute.return_value = _make_execute_result([m])
    _make_refresh_side_effect(mock_session)
    service = ModelService(mock_session)

    result = await service.update_model(m.id, ModelUpdate(display_name="New Name"))

    assert result.display_name == "New Name"
    mock_session.commit.assert_awaited()


async def test_update_model_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _make_execute_result([])
    service = ModelService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_model(uuid.uuid4(), ModelUpdate(display_name="X"))

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ── delete_model ──────────────────────────────────────────────────────────────


async def test_delete_model_success(mock_session, model_factory):
    m = model_factory(is_default=False)
    mock_session.execute.return_value = _make_execute_result([m])
    service = ModelService(mock_session)

    await service.delete_model(m.id)

    mock_session.delete.assert_awaited_once_with(m)
    mock_session.commit.assert_awaited_once()


async def test_delete_default_model_raises_409(mock_session, model_factory):
    m = model_factory(is_default=True)
    mock_session.execute.return_value = _make_execute_result([m])
    service = ModelService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_model(m.id)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_model_service.py -x -vv
```

Expected: `ImportError` — `ModelCreate`, `ModelService` do not exist yet.

- [ ] **Step 3: Create `backend/src/schemas/llm_model.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class ModelCreate(BaseModel):
    display_name: str
    model_id: str
    provider: str
    description: str | None = None
    base_url: str | None = None
    is_active: bool = True
    is_default: bool = False


class ModelRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    display_name: str
    model_id: str
    provider: str
    description: str | None
    base_url: str | None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ModelUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    base_url: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
```

- [ ] **Step 4: Create `backend/src/services/model_service.py`**

```python
import uuid

from aegra_api.core.orm import get_session
from fastapi import Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.llm_model import LLMModel
from src.schemas.llm_model import ModelCreate, ModelRead, ModelUpdate


class ModelService:
    """Handles all database operations for the LLMModel entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _fetch_model(self, model_id: object) -> LLMModel:
        result = await self.session.execute(
            select(LLMModel).where(LLMModel.id == model_id)
        )
        m = result.scalar_one_or_none()
        if m is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found",
            )
        return m

    async def _set_default(self, model_id: object) -> ModelRead:
        await self.session.execute(update(LLMModel).values(is_default=False))
        await self.session.execute(
            update(LLMModel)
            .where(LLMModel.id == model_id)
            .values(is_default=True)
        )
        await self.session.commit()
        return await self.get_model(model_id)

    async def create_model(self, data: ModelCreate) -> ModelRead:
        m = LLMModel(  # type: ignore[call-arg]
            display_name=data.display_name,
            model_id=data.model_id,
            provider=data.provider,
            description=data.description,
            base_url=data.base_url,
            is_active=data.is_active,
            is_default=False,
        )
        self.session.add(m)
        await self.session.commit()
        await self.session.refresh(m)
        if data.is_default:
            return await self._set_default(m.id)
        return ModelRead.model_validate(m)

    async def get_model(self, model_id: object) -> ModelRead:
        return ModelRead.model_validate(await self._fetch_model(model_id))

    async def list_active_models(self) -> list[ModelRead]:
        result = await self.session.execute(
            select(LLMModel).where(LLMModel.is_active == True)  # noqa: E712
        )
        return [ModelRead.model_validate(m) for m in result.scalars().all()]

    async def list_all_models(self) -> list[ModelRead]:
        result = await self.session.execute(select(LLMModel))
        return [ModelRead.model_validate(m) for m in result.scalars().all()]

    async def update_model(self, model_id: object, data: ModelUpdate) -> ModelRead:
        m = await self._fetch_model(model_id)
        update_data = data.model_dump(exclude_none=True, exclude={"is_default"})
        for field, value in update_data.items():
            setattr(m, field, value)
        await self.session.commit()
        await self.session.refresh(m)
        if data.is_default is True:
            return await self._set_default(model_id)
        return ModelRead.model_validate(m)

    async def delete_model(self, model_id: object) -> None:
        m = await self._fetch_model(model_id)
        if m.is_default:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete the default model. Set another model as default first.",
            )
        await self.session.delete(m)
        await self.session.commit()


def get_model_service(
    session: AsyncSession = Depends(get_session),
) -> ModelService:
    return ModelService(session)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_model_service.py -x -vv
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add src/schemas/llm_model.py src/services/model_service.py tests/conftest.py tests/test_model_service.py
git commit -m "feat: add LLMModel schemas and ModelService"
```

---

## Task 4: Models API routes

**Files:**
- Create: `backend/src/api/routes/models.py`
- Modify: `backend/src/main.py`
- Create: `backend/tests/test_routes_models.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_routes_models.py`:

```python
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from src.core.security import get_current_admin, get_current_user
from src.schemas.llm_model import ModelCreate, ModelRead
from src.schemas.user import UserRead
from src.services.model_service import ModelService, get_model_service

_HTTP_200 = 200
_HTTP_201 = 201
_HTTP_204 = 204
_HTTP_401 = 401
_HTTP_403 = 403
_HTTP_404 = 404
_HTTP_409 = 409


def _make_user_read(**kwargs) -> UserRead:
    return UserRead(
        id=kwargs.get("id", uuid.uuid4()),
        name="Admin User",
        email="admin@example.com",
        is_admin=kwargs.get("is_admin", True),
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_model_read(**kwargs) -> ModelRead:
    return ModelRead(
        id=kwargs.get("id", uuid.uuid4()),
        display_name=kwargs.get("display_name", "GPT-4o"),
        model_id=kwargs.get("model_id", "openai/gpt-4o"),
        provider=kwargs.get("provider", "openai"),
        description=None,
        base_url=None,
        is_active=kwargs.get("is_active", True),
        is_default=kwargs.get("is_default", False),
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _async_client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


# ── GET /api/v1/models ────────────────────────────────────────────────────────


async def test_list_active_models_requires_auth(test_app):
    async with _async_client(test_app) as client:
        res = await client.get("/api/v1/models")
    assert res.status_code == _HTTP_401


async def test_list_active_models_returns_active_only(test_app):
    models = [_make_model_read(is_active=True)]
    mock_service = AsyncMock(spec=ModelService)
    mock_service.list_active_models.return_value = models

    test_app.dependency_overrides[get_current_user] = lambda: _make_user_read(is_admin=False)
    test_app.dependency_overrides[get_model_service] = lambda: mock_service

    async with _async_client(test_app) as client:
        res = await client.get("/api/v1/models")

    assert res.status_code == _HTTP_200
    data = res.json()
    assert len(data) == 1
    assert data[0]["model_id"] == "openai/gpt-4o"


# ── GET /api/v1/models/all ────────────────────────────────────────────────────


async def test_list_all_models_requires_admin(test_app):
    test_app.dependency_overrides[get_current_user] = lambda: _make_user_read(is_admin=False)
    test_app.dependency_overrides[get_current_admin] = lambda: (_ for _ in ()).throw(
        HTTPException(status_code=403, detail="Admin access required")
    )

    async with _async_client(test_app) as client:
        res = await client.get(
            "/api/v1/models/all",
            headers={"Authorization": "Bearer fake"},
        )

    assert res.status_code == _HTTP_403


async def test_list_all_models_returns_all(test_app):
    models = [
        _make_model_read(is_active=True),
        _make_model_read(model_id="openai/gpt-3.5-turbo", is_active=False),
    ]
    mock_service = AsyncMock(spec=ModelService)
    mock_service.list_all_models.return_value = models

    test_app.dependency_overrides[get_current_admin] = lambda: _make_user_read()
    test_app.dependency_overrides[get_model_service] = lambda: mock_service

    async with _async_client(test_app) as client:
        res = await client.get("/api/v1/models/all")

    assert res.status_code == _HTTP_200
    assert len(res.json()) == 2


# ── POST /api/v1/models ───────────────────────────────────────────────────────


async def test_create_model_requires_admin(test_app):
    test_app.dependency_overrides[get_current_user] = lambda: _make_user_read(is_admin=False)

    async with _async_client(test_app) as client:
        res = await client.post(
            "/api/v1/models",
            json={"display_name": "X", "model_id": "openai/gpt-4o", "provider": "openai"},
            headers={"Authorization": "Bearer fake"},
        )

    assert res.status_code == _HTTP_403


async def test_create_model_success(test_app):
    created = _make_model_read()
    mock_service = AsyncMock(spec=ModelService)
    mock_service.create_model.return_value = created

    test_app.dependency_overrides[get_current_admin] = lambda: _make_user_read()
    test_app.dependency_overrides[get_model_service] = lambda: mock_service

    async with _async_client(test_app) as client:
        res = await client.post(
            "/api/v1/models",
            json={"display_name": "GPT-4o", "model_id": "openai/gpt-4o", "provider": "openai"},
        )

    assert res.status_code == _HTTP_201
    assert res.json()["model_id"] == "openai/gpt-4o"


# ── DELETE /api/v1/models/{id} ────────────────────────────────────────────────


async def test_delete_default_model_returns_409(test_app):
    mock_service = AsyncMock(spec=ModelService)
    mock_service.delete_model.side_effect = HTTPException(
        status_code=_HTTP_409,
        detail="Cannot delete the default model. Set another model as default first.",
    )

    test_app.dependency_overrides[get_current_admin] = lambda: _make_user_read()
    test_app.dependency_overrides[get_model_service] = lambda: mock_service

    async with _async_client(test_app) as client:
        res = await client.delete(f"/api/v1/models/{uuid.uuid4()}")

    assert res.status_code == _HTTP_409
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_routes_models.py -x -vv
```

Expected: `ImportError` — routes not registered yet.

- [ ] **Step 3: Create `backend/src/api/routes/models.py`**

```python
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.security import get_current_admin, get_current_user
from src.schemas.llm_model import ModelCreate, ModelRead, ModelUpdate
from src.services.model_service import ModelService, get_model_service

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("", dependencies=[Depends(get_current_user)])
async def list_active_models(
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> list[ModelRead]:
    """List models visible to users (is_active=True)."""
    return await model_service.list_active_models()


@router.get("/all", dependencies=[Depends(get_current_admin)])
async def list_all_models(
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> list[ModelRead]:
    """List all models including inactive ones. Admin only."""
    return await model_service.list_all_models()


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
async def create_model(
    data: ModelCreate,
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> ModelRead:
    """Create a new model. Admin only."""
    return await model_service.create_model(data)


@router.patch("/{model_id}", dependencies=[Depends(get_current_admin)])
async def update_model(
    model_id: uuid.UUID,
    data: ModelUpdate,
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> ModelRead:
    """Partially update a model. Admin only."""
    return await model_service.update_model(model_id, data)


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
async def delete_model(
    model_id: uuid.UUID,
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> None:
    """Delete a model. Returns 409 if the model is the current default. Admin only."""
    await model_service.delete_model(model_id)
```

- [ ] **Step 4: Register the router in `backend/src/main.py`**

```python
from fastapi import FastAPI

from src.api.routes.auth import router as auth_router
from src.api.routes.models import router as models_router
from src.api.routes.users import router as users_router

app = FastAPI()


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "FastAPI is running!"}


app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_routes_models.py -x -vv
```

Expected: all tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
cd backend && uv run pytest -x -vv
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
cd backend
git add src/api/routes/models.py src/main.py tests/test_routes_models.py
git commit -m "feat: add /api/v1/models REST endpoints"
```

---

## Task 5: Frontend UI components (Select + Tabs)

**Files:**
- Create: `frontend/components/ui/select.tsx`
- Create: `frontend/components/ui/tabs.tsx`

These wrap `@base-ui/react` primitives following the same pattern as existing components (e.g., `dialog.tsx`, `dropdown-menu.tsx`).

- [ ] **Step 1: Create `frontend/components/ui/select.tsx`**

```tsx
"use client"

import * as React from "react"
import { Select as SelectPrimitive } from "@base-ui/react/select"
import { cn } from "@/lib/utils"
import { CheckIcon, ChevronDownIcon } from "lucide-react"

function Select<Value>({ ...props }: SelectPrimitive.Root.Props<Value>) {
  return <SelectPrimitive.Root data-slot="select" {...props} />
}

function SelectTrigger({
  className,
  children,
  ...props
}: SelectPrimitive.Trigger.Props) {
  return (
    <SelectPrimitive.Trigger
      data-slot="select-trigger"
      className={cn(
        "flex h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs ring-offset-background focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
      <ChevronDownIcon className="size-4 shrink-0 opacity-50 pointer-events-none" />
    </SelectPrimitive.Trigger>
  )
}

function SelectValue({ className, ...props }: SelectPrimitive.Value.Props) {
  return (
    <SelectPrimitive.Value
      data-slot="select-value"
      className={cn("flex-1 text-left truncate", className)}
      {...props}
    />
  )
}

function SelectContent({
  className,
  children,
  ...props
}: SelectPrimitive.Popup.Props) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Positioner sideOffset={4} className="z-50">
        <SelectPrimitive.Popup
          data-slot="select-content"
          className={cn(
            "min-w-[var(--anchor-width)] rounded-md border bg-popover text-popover-foreground shadow-md",
            "data-[ending-style]:animate-out data-[ending-style]:fade-out-0 data-[ending-style]:zoom-out-95",
            "data-[starting-style]:animate-in data-[starting-style]:fade-in-0 data-[starting-style]:zoom-in-95",
            className
          )}
          {...props}
        >
          <SelectPrimitive.List className="p-1">{children}</SelectPrimitive.List>
        </SelectPrimitive.Popup>
      </SelectPrimitive.Positioner>
    </SelectPrimitive.Portal>
  )
}

function SelectItem({
  className,
  children,
  ...props
}: SelectPrimitive.Item.Props) {
  return (
    <SelectPrimitive.Item
      data-slot="select-item"
      className={cn(
        "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className
      )}
      {...props}
    >
      <span className="absolute left-2 flex size-3.5 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <CheckIcon className="size-4" />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  )
}

export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem }
```

- [ ] **Step 2: Create `frontend/components/ui/tabs.tsx`**

```tsx
"use client"

import * as React from "react"
import { Tabs as TabsPrimitive } from "@base-ui/react/tabs"
import { cn } from "@/lib/utils"

function Tabs({ ...props }: TabsPrimitive.Root.Props) {
  return <TabsPrimitive.Root data-slot="tabs" {...props} />
}

function TabsList({ className, ...props }: TabsPrimitive.List.Props) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      className={cn(
        "inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

function TabsTrigger({ className, ...props }: TabsPrimitive.Tab.Props) {
  return (
    <TabsPrimitive.Tab
      data-slot="tabs-trigger"
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[selected]:bg-background data-[selected]:text-foreground data-[selected]:shadow",
        className
      )}
      {...props}
    />
  )
}

function TabsContent({ className, ...props }: TabsPrimitive.Panel.Props) {
  return (
    <TabsPrimitive.Panel
      data-slot="tabs-content"
      className={cn(
        "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        className
      )}
      {...props}
    />
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }
```

- [ ] **Step 3: Commit**

```bash
cd frontend
git add components/ui/select.tsx components/ui/tabs.tsx
git commit -m "feat: add Select and Tabs UI components (@base-ui/react)"
```

---

## Task 6: Frontend types + API layer + hooks

**Files:**
- Modify: `frontend/lib/types.ts`
- Create: `frontend/lib/api/models.ts`
- Create: `frontend/lib/hooks/useModels.ts`
- Modify: `frontend/lib/hooks/useThreads.ts`

- [ ] **Step 1: Update `frontend/lib/types.ts`**

Add after the existing `UserUpdate` block (before `TokenResponse`):

```typescript
export interface ModelRead {
  id: string
  display_name: string
  model_id: string
  provider: string
  description: string | null
  base_url: string | null
  is_active: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface ModelCreate {
  display_name: string
  model_id: string
  provider: string
  description?: string
  base_url?: string
  is_active?: boolean
  is_default?: boolean
}

export interface ModelUpdate {
  display_name?: string
  description?: string
  base_url?: string
  is_active?: boolean
  is_default?: boolean
}
```

Also update `ThreadRead.metadata` to add typed optional fields:

```typescript
export interface ThreadRead {
  thread_id: string
  status: "idle" | "busy" | "interrupted" | "error"
  metadata: {
    assistant_id?: string | null
    thread_assistant_id?: string
    thread_name?: string
    thread_model?: string
    thread_model_base_url?: string | null
    owner?: string
    [key: string]: unknown
  }
  created_at: string
  updated_at: string
}
```

- [ ] **Step 2: Create `frontend/lib/api/models.ts`**

```typescript
import { apiClient } from "./client"
import type { ModelCreate, ModelRead, ModelUpdate } from "@/lib/types"

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

export async function fetchModels(): Promise<ModelRead[]> {
  const res = await apiClient("/api/v1/models")
  if (!res.ok) return throwOnError(res, "Failed to fetch models")
  return res.json()
}

export async function fetchAllModels(): Promise<ModelRead[]> {
  const res = await apiClient("/api/v1/models/all")
  if (!res.ok) return throwOnError(res, "Failed to fetch all models")
  return res.json()
}

export async function createModel(data: ModelCreate): Promise<ModelRead> {
  const res = await apiClient("/api/v1/models", {
    method: "POST",
    body: JSON.stringify(data),
  })
  if (!res.ok) return throwOnError(res, "Failed to create model")
  return res.json()
}

export async function updateModel(id: string, data: ModelUpdate): Promise<ModelRead> {
  const res = await apiClient(`/api/v1/models/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
  if (!res.ok) return throwOnError(res, "Failed to update model")
  return res.json()
}

export async function deleteModel(id: string): Promise<void> {
  const res = await apiClient(`/api/v1/models/${id}`, { method: "DELETE" })
  if (!res.ok) return throwOnError(res, "Failed to delete model")
}
```

- [ ] **Step 3: Create `frontend/lib/hooks/useModels.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createModel,
  deleteModel,
  fetchAllModels,
  fetchModels,
  updateModel,
} from "@/lib/api/models"
import type { ModelCreate, ModelUpdate } from "@/lib/types"

export const MODELS_KEY = ["models"]

export function useModels() {
  return useQuery({
    queryKey: MODELS_KEY,
    queryFn: fetchModels,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAllModels() {
  return useQuery({
    queryKey: [...MODELS_KEY, "all"],
    queryFn: fetchAllModels,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ModelCreate) => createModel(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODELS_KEY })
    },
  })
}

export function useUpdateModel(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ModelUpdate) => updateModel(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODELS_KEY })
    },
  })
}

export function useSetModelDefault() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => updateModel(id, { is_default: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODELS_KEY })
    },
  })
}

export function useDeleteModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteModel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MODELS_KEY })
    },
  })
}
```

- [ ] **Step 4: Update `frontend/lib/hooks/useThreads.ts`**

Add `useThread` and `useUpdateThreadModel` after the existing hooks:

```typescript
export function useThread(threadId: string) {
  return useQuery({
    queryKey: THREADS_KEY,
    queryFn: fetchThreads,
    select: (threads) => threads.find((t) => t.thread_id === threadId),
  })
}

export function useUpdateThreadModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      modelId,
      baseUrl,
    }: {
      id: string
      modelId: string
      baseUrl: string | null
    }) =>
      updateThreadMetadata(id, {
        thread_model: modelId,
        thread_model_base_url: baseUrl,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: THREADS_KEY }),
  })
}
```

- [ ] **Step 5: Commit**

```bash
cd frontend
git add lib/types.ts lib/api/models.ts lib/hooks/useModels.ts lib/hooks/useThreads.ts
git commit -m "feat: add model types, API layer, and TanStack Query hooks"
```

---

## Task 7: Admin model management UI

**Files:**
- Create: `frontend/components/admin/ModelForm.tsx`
- Create: `frontend/components/admin/AdminModelTable.tsx`
- Modify: `frontend/app/(app)/(chat)/admin/page.tsx`

- [ ] **Step 1: Create `frontend/components/admin/ModelForm.tsx`**

```tsx
"use client"

import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useCreateModel, useUpdateModel } from "@/lib/hooks/useModels"
import type { ModelRead } from "@/lib/types"

const PROVIDERS = ["anthropic", "openai", "ollama", "custom"] as const

const schema = z.object({
  display_name: z.string().min(1, "Nome obrigatório"),
  model_id: z.string().min(1, "Model ID obrigatório"),
  provider: z.enum(PROVIDERS),
  description: z.string().optional(),
  base_url: z.string().url("URL inválida").optional().or(z.literal("")),
  is_active: z.boolean(),
  is_default: z.boolean(),
})

type FormData = z.infer<typeof schema>

interface ModelFormProps {
  open: boolean
  onClose: () => void
  model?: ModelRead
}

export function ModelForm({ open, onClose, model }: ModelFormProps) {
  const createModel = useCreateModel()
  const updateModel = useUpdateModel(model?.id ?? "")

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: "",
      model_id: "",
      provider: "anthropic",
      description: "",
      base_url: "",
      is_active: true,
      is_default: false,
    },
  })

  useEffect(() => {
    if (model) {
      reset({
        display_name: model.display_name,
        model_id: model.model_id,
        provider: model.provider as (typeof PROVIDERS)[number],
        description: model.description ?? "",
        base_url: model.base_url ?? "",
        is_active: model.is_active,
        is_default: model.is_default,
      })
    } else {
      reset({
        display_name: "",
        model_id: "",
        provider: "anthropic",
        description: "",
        base_url: "",
        is_active: true,
        is_default: false,
      })
    }
  }, [model, open, reset])

  const selectedProvider = watch("provider")
  const isActive = watch("is_active")
  const isDefault = watch("is_default")

  async function onSubmit(data: FormData) {
    const payload = {
      display_name: data.display_name,
      model_id: data.model_id,
      provider: data.provider,
      description: data.description || undefined,
      base_url: data.base_url || undefined,
      is_active: data.is_active,
      is_default: data.is_default,
    }
    try {
      if (model) {
        const { model_id: _, provider: __, ...updatePayload } = payload
        await updateModel.mutateAsync(updatePayload)
        toast.success("Modelo atualizado")
      } else {
        await createModel.mutateAsync(payload)
        toast.success("Modelo criado")
      }
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
            {model ? "editar modelo" : "novo modelo"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
          <div className="space-y-1">
            <Label className="font-mono text-xs">display_name</Label>
            <Input {...register("display_name")} placeholder="Claude Sonnet 4.6" />
            {errors.display_name && (
              <p className="text-xs text-destructive">{errors.display_name.message}</p>
            )}
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">model_id</Label>
            <Input
              {...register("model_id")}
              placeholder="anthropic/claude-sonnet-4-6"
              className="font-mono text-sm"
              disabled={!!model}
            />
            {errors.model_id && (
              <p className="text-xs text-destructive">{errors.model_id.message}</p>
            )}
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">provider</Label>
            {model ? (
              <p className="text-sm text-muted-foreground font-mono">{model.provider}</p>
            ) : (
              <Select
                value={selectedProvider}
                onValueChange={(v) => setValue("provider", v as (typeof PROVIDERS)[number])}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">description</Label>
            <Textarea
              {...register("description")}
              placeholder="Descrição opcional"
              className="font-mono text-sm min-h-16"
            />
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">base_url</Label>
            <Input
              {...register("base_url")}
              placeholder="https://litellm.empresa.com/v1"
              className="font-mono text-sm"
            />
            {errors.base_url && (
              <p className="text-xs text-destructive">{errors.base_url.message}</p>
            )}
          </div>

          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setValue("is_active", e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-mono">ativo</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isDefault}
                onChange={(e) => setValue("is_default", e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-mono">padrão</span>
            </label>
          </div>

          <div className="flex gap-2 pt-1">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="flex-1"
              style={{ backgroundColor: "#2a9d8f" }}
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

- [ ] **Step 2: Create `frontend/components/admin/AdminModelTable.tsx`**

```tsx
"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Pencil, Plus, Star, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { useAllModels, useDeleteModel, useSetModelDefault } from "@/lib/hooks/useModels"
import { ModelForm } from "./ModelForm"
import type { ModelRead } from "@/lib/types"

export function AdminModelTable() {
  const [formOpen, setFormOpen] = useState(false)
  const [editingModel, setEditingModel] = useState<ModelRead | undefined>()
  const { data: models, isLoading } = useAllModels()
  const deleteModel = useDeleteModel()
  const setDefault = useSetModelDefault()

  function handleEdit(model: ModelRead) {
    setEditingModel(model)
    setFormOpen(true)
  }

  function handleNew() {
    setEditingModel(undefined)
    setFormOpen(true)
  }

  async function handleDelete(id: string) {
    try {
      await deleteModel.mutateAsync(id)
      toast.success("Modelo removido")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao remover")
    }
  }

  async function handleSetDefault(model: ModelRead) {
    try {
      await setDefault.mutateAsync(model.id)
      toast.success(`"${model.display_name}" definido como padrão`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao definir padrão")
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button
          size="sm"
          className="font-mono text-xs gap-1"
          style={{ backgroundColor: "#2a9d8f" }}
          onClick={handleNew}
        >
          <Plus size={12} />
          novo modelo
        </Button>
      </div>

      <div className="border border-border rounded-md overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-mono text-xs">nome</TableHead>
              <TableHead className="font-mono text-xs">model_id</TableHead>
              <TableHead className="font-mono text-xs">provider</TableHead>
              <TableHead className="font-mono text-xs">base_url</TableHead>
              <TableHead className="font-mono text-xs">status</TableHead>
              <TableHead className="font-mono text-xs w-[120px]">ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-full" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : (models ?? []).map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-1">
                        {m.display_name}
                        {m.is_default && (
                          <Star size={12} style={{ color: "#2a9d8f" }} />
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{m.model_id}</TableCell>
                    <TableCell className="font-mono text-xs">{m.provider}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground truncate max-w-[160px]">
                      {m.base_url ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={m.is_active ? "outline" : "secondary"}
                        className="font-mono text-xs"
                      >
                        {m.is_active ? "ativo" : "inativo"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => handleEdit(m)}
                        >
                          <Pencil size={12} />
                        </Button>
                        {!m.is_default && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-foreground"
                            title="Definir como padrão"
                            onClick={() => handleSetDefault(m)}
                          >
                            <Star size={12} />
                          </Button>
                        )}
                        <AlertDialog>
                          <AlertDialogTrigger
                            render={
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-destructive hover:bg-destructive/10"
                                disabled={m.is_default}
                                title={
                                  m.is_default
                                    ? "Não é possível deletar o modelo padrão"
                                    : "Deletar"
                                }
                              />
                            }
                          >
                            <Trash2 size={12} />
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle className="font-mono">
                                deletar modelo?
                              </AlertDialogTitle>
                              <AlertDialogDescription>
                                O modelo <strong>{m.display_name}</strong> será removido
                                permanentemente.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>cancelar</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleDelete(m.id)}
                                className="bg-destructive hover:bg-destructive/90"
                              >
                                deletar
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-muted-foreground font-mono">
        {(models ?? []).length} modelo{(models ?? []).length !== 1 ? "s" : ""}
      </p>

      <ModelForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        model={editingModel}
      />
    </div>
  )
}
```

- [ ] **Step 3: Update `frontend/app/(app)/(chat)/admin/page.tsx`**

```tsx
"use client"

import { useAuthStore } from "@/lib/store/auth"
import { AdminUserTable } from "@/components/admin/AdminUserTable"
import { AdminModelTable } from "@/components/admin/AdminModelTable"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
        <p className="font-mono text-sm text-muted-foreground">
          restricted to administrators
        </p>
        <Button variant="outline" onClick={() => router.push("/assistants")}>
          go back
        </Button>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-6xl w-full">
      <div className="flex items-center gap-2 mb-6">
        <ShieldCheck size={20} style={{ color: "#2a9d8f" }} />
        <h1 className="text-xl font-mono font-semibold" style={{ color: "#2a9d8f" }}>
          admin
        </h1>
      </div>
      <Tabs defaultValue="users">
        <TabsList className="mb-6">
          <TabsTrigger value="users" className="font-mono text-xs">
            usuários
          </TabsTrigger>
          <TabsTrigger value="models" className="font-mono text-xs">
            modelos
          </TabsTrigger>
        </TabsList>
        <TabsContent value="users">
          <AdminUserTable />
        </TabsContent>
        <TabsContent value="models">
          <AdminModelTable />
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
cd frontend
git add components/admin/ModelForm.tsx components/admin/AdminModelTable.tsx app/"(app)/(chat)"/admin/page.tsx
git commit -m "feat: add admin model management UI with tabbed layout"
```

---

## Task 8: Remove model from AssistantForm

**Files:**
- Modify: `frontend/components/assistants/AssistantForm.tsx`

- [ ] **Step 1: Update the Zod schema** — remove the `model` field:

```typescript
const schema = z.object({
  name: z.string().min(1, "Nome obrigatório"),
  description: z.string().optional(),
  graph_id: z.string().min(1),
  system_prompt: z.string().optional(),
})
```

- [ ] **Step 2: Update the form values** — remove `model` from `values`:

```typescript
  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    values: {
      name: assistant?.name ?? "",
      description: assistant?.description ?? "",
      graph_id: assistant?.graph_id ?? GRAPH_TYPES[0]?.graph_id ?? "agent",
      system_prompt:
        (assistant?.context as { system_prompt?: string })?.system_prompt ?? "",
    },
  })
```

- [ ] **Step 3: Update the submit payload** — remove `model` from context:

```typescript
    const payload = {
      name: data.name,
      description: data.description || undefined,
      graph_id: data.graph_id,
      context: {
        ...(data.system_prompt ? { system_prompt: data.system_prompt } : {}),
      },
    }
```

- [ ] **Step 4: Remove the model JSX field** — delete the entire block:

```tsx
          <div className="space-y-1">
            <Label className="font-mono text-xs">model</Label>
            <Input
              {...register("model")}
              placeholder="anthropic/claude-sonnet-4-6"
              className="font-mono text-sm"
            />
          </div>
```

- [ ] **Step 5: Commit**

```bash
cd frontend
git add components/assistants/AssistantForm.tsx
git commit -m "feat: remove model field from AssistantForm (model is now per-thread)"
```

---

## Task 9: ChatView model selector

**Files:**
- Modify: `frontend/components/chat/ChatView.tsx`

- [ ] **Step 1: Add model selector state and hooks**

Add these imports at the top of `ChatView.tsx` (the `useEffect`, `useRef`, `useState` import line is already there — only add the new lines):

```typescript
import { useModels } from "@/lib/hooks/useModels"
import { useThread, useUpdateThreadModel } from "@/lib/hooks/useThreads"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
```

- [ ] **Step 2: Add model selector logic inside `ChatView`**

Add these inside the `ChatView` function body, after the existing hook declarations:

```typescript
  const { data: models } = useModels()
  const { data: thread } = useThread(threadId)
  const updateThreadModel = useUpdateThreadModel()
  const [selectedModelId, setSelectedModelId] = useState<string | undefined>(undefined)

  // Initialize selectedModelId from thread metadata or the default model
  useEffect(() => {
    if (!models?.length) return
    const saved = thread?.metadata?.thread_model
    const defaultId = models.find((m) => m.is_default)?.model_id
    setSelectedModelId((saved as string | undefined) ?? defaultId ?? models[0]?.model_id)
  }, [models, thread])

  const selectedModel = models?.find((m) => m.model_id === selectedModelId)

  function handleModelChange(modelId: string) {
    const m = models?.find((m) => m.model_id === modelId)
    if (!m) return
    setSelectedModelId(modelId)
    updateThreadModel.mutate({
      id: threadId,
      modelId,
      baseUrl: m.base_url ?? null,
    })
  }
```

- [ ] **Step 3: Update `handleSubmit` to pass model config**

Replace the existing `handleSubmit` function:

```typescript
  function handleSubmit(content: string) {
    submit(
      { messages: [{ role: "human", content }] },
      {
        config: {
          configurable: {
            model: selectedModelId,
            model_base_url: selectedModel?.base_url ?? null,
          },
        },
      }
    )
  }
```

- [ ] **Step 4: Add the model selector above `ChatInput` in the JSX**

Replace the closing section of the return statement:

```tsx
      <div className="border-t border-border/60">
        {models && models.length > 0 && (
          <div className="px-4 pt-3 pb-0">
            <Select
              value={selectedModelId}
              onValueChange={handleModelChange}
              disabled={isStreaming}
            >
              <SelectTrigger className="h-7 text-xs font-mono border-border/60 bg-transparent w-auto min-w-[180px]">
                <SelectValue placeholder="selecionar modelo..." />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.model_id} value={m.model_id} className="font-mono text-xs">
                    {m.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        <ChatInput
          onSubmit={handleSubmit}
          onStop={stop}
          isStreaming={isStreaming}
        />
      </div>
```

The full return statement JSX structure should be:

```tsx
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

      <div className="border-t border-border/60">
        {models && models.length > 0 && (
          <div className="px-4 pt-3 pb-0">
            <Select
              value={selectedModelId}
              onValueChange={handleModelChange}
              disabled={isStreaming}
            >
              <SelectTrigger className="h-7 text-xs font-mono border-border/60 bg-transparent w-auto min-w-[180px]">
                <SelectValue placeholder="selecionar modelo..." />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.model_id} value={m.model_id} className="font-mono text-xs">
                    {m.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        <ChatInput
          onSubmit={handleSubmit}
          onStop={stop}
          isStreaming={isStreaming}
        />
      </div>
    </div>
  )
```

- [ ] **Step 5: Run TypeScript check**

```bash
cd frontend && npm run build 2>&1 | head -40
```

Expected: no TypeScript errors related to the new changes.

- [ ] **Step 6: Commit**

```bash
cd frontend
git add components/chat/ChatView.tsx
git commit -m "feat: add per-thread model selector to ChatView"
```

---

## Post-implementation checklist

- [ ] Start backend: `cd backend && uv run aegra dev` — verify no import errors
- [ ] Start frontend: `cd frontend && npm run dev` — verify app loads
- [ ] Run all backend tests: `cd backend && uv run pytest -x -vv` — all pass
- [ ] Seed a model via the admin panel (`/admin` → Modelos tab → novo modelo)
- [ ] Open a chat thread, verify the model selector appears with the seeded model
- [ ] Select a different model, send a message, verify the correct model responds
- [ ] Reload the thread, verify the model selection is restored from metadata
