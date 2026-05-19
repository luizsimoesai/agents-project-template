"""Runtime model selection: shared context schema and middleware for all agents."""

from __future__ import annotations

import functools
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any, cast

from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage


@dataclass(kw_only=True)
class Context:
    """Runtime configuration injected into agent graphs via config.configurable."""

    model: Annotated[
        str, {"description": "LLM model as 'provider/model' or 'provider:model'."}
    ] = field(
        default="",
    )
    model_base_url: Annotated[
        str | None, {"description": "Optional base URL for Ollama or proxy servers."}
    ] = field(default=None)
    # Per-assistant discriminator written by the create form to bypass Aegra's
    # UNIQUE (user_id, graph_id, config) index. Read nowhere at runtime — only
    # declared here so the dataclass accepts it when LangGraph builds context
    # from the assistant's stored config.configurable.
    client_id: str | None = field(default=None)
    # Overrides the graph's static system_prompt at runtime. Applied by the
    # dynamic_system_prompt middleware below.
    system_prompt: Annotated[
        str | None,
        {"description": "Optional system prompt that overrides the graph default."},
    ] = field(default=None)

    def __post_init__(self) -> None:
        if not self.model and (env_model := os.environ.get("MODEL")):
            self.model = env_model
        if self.model_base_url is None and (
            env_base_url := os.environ.get("MODEL_BASE_URL")
        ):
            self.model_base_url = env_base_url


def _split_provider(model_id: str) -> tuple[str, str] | None:
    """Split 'provider/model' or 'provider:model' into (provider, model).

    Returns None when no separator is found (so init_chat_model can apply
    its own native parsing — which already supports 'provider:model').

    The first occurrence of '/' or ':' wins, so 'ollama/llama3:8b' parses to
    ('ollama', 'llama3:8b') — the inner ':' is preserved as part of the tag.
    """
    slash = model_id.find("/")
    colon = model_id.find(":")
    if slash < 0 and colon < 0:
        return None
    if slash >= 0 and (colon < 0 or slash < colon):
        provider, model = model_id.split("/", maxsplit=1)
    else:
        provider, model = model_id.split(":", maxsplit=1)
    return provider.strip(), model.strip()


@functools.lru_cache(maxsize=32)
def _load(model_id: str, base_url: str | None = None) -> BaseChatModel:
    kwargs: dict[str, Any] = {}
    if base_url:
        kwargs["base_url"] = base_url
    parts = _split_provider(model_id)
    if parts is None:
        return cast(BaseChatModel, init_chat_model(model_id, **kwargs))
    provider, model = parts
    return cast(
        BaseChatModel, init_chat_model(model, model_provider=provider, **kwargs)
    )


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


@wrap_model_call  # type: ignore[arg-type]
async def dynamic_system_prompt(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Override the graph's static system_prompt with the assistant's, if any.

    Assistants are configured per-user in the UI; their ``context.system_prompt``
    flows in via ``config.configurable.system_prompt``. When set, we replace the
    request's ``system_message`` for this call only — state isn't mutated.

    Documented pattern: https://docs.langchain.com/oss/python/langchain/middleware/custom#dynamic-prompt
    """
    ctx = request.runtime.context
    prompt = getattr(ctx, "system_prompt", None) if ctx else None
    if prompt:
        return await handler(
            request.override(system_message=SystemMessage(content=prompt))
        )
    # mypy: the typed Callable[[ModelRequest], ModelResponse] hides the fact
    # that the wrap_model_call adapter returns an awaitable in async mode.
    return await handler(request)  # type: ignore[misc, no-any-return]
