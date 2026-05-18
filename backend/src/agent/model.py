"""Runtime model selection middleware shared by all agents."""

from __future__ import annotations

import functools
from typing import Callable

from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


@functools.lru_cache(maxsize=32)
def _load(model_id: str, base_url: str | None = None) -> BaseChatModel:
    provider, model = model_id.split("/", maxsplit=1)
    kwargs: dict = {}
    if base_url:
        kwargs["base_url"] = base_url
    return init_chat_model(model.strip(), model_provider=provider.strip(), **kwargs)


@wrap_model_call
def configurable_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Select the model from runtime context on every invocation."""
    ctx = request.runtime.context
    if not ctx or not ctx.model:
        raise ValueError(
            "No model configured. Set MODEL in .env or pass model via context."
        )
    model = _load(ctx.model, getattr(ctx, "model_base_url", None))
    return handler(request.override(model=model))
