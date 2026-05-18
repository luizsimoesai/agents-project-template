"""Runtime model selection: shared context schema and middleware for all agents."""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass, field
from typing import Annotated, Callable

from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


@dataclass(kw_only=True)
class Context:
    """Runtime configuration injected into agent graphs via config.configurable."""

    model: Annotated[str, {"description": "LLM model as 'provider/model'."}] = field(
        default="",
    )
    model_base_url: Annotated[
        str | None, {"description": "Optional base URL for Ollama or proxy servers."}
    ] = field(default=None)

    def __post_init__(self) -> None:
        if not self.model:
            if env_model := os.environ.get("MODEL"):
                self.model = env_model
        if self.model_base_url is None:
            if env_base_url := os.environ.get("MODEL_BASE_URL"):
                self.model_base_url = env_base_url


@functools.lru_cache(maxsize=32)
def _load(model_id: str, base_url: str | None = None) -> BaseChatModel:
    provider, model = model_id.split("/", maxsplit=1)
    kwargs: dict = {}
    if base_url:
        kwargs["base_url"] = base_url
    return init_chat_model(model.strip(), model_provider=provider.strip(), **kwargs)


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
