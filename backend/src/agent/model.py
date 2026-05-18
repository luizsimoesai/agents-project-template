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
    return await handler(request.override(model=model))
