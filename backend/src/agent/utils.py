"""Utility functions and graph-agnostic model proxy for the backend."""

from __future__ import annotations

import functools
import os
from collections.abc import Callable, Sequence
from typing import Any, AsyncIterator, Iterator

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import Field


def load_chat_model(
    fully_specified_name: str,
    *,
    base_url: str | None = None,
) -> BaseChatModel:
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
    provider, model = provider.strip(), model.strip()
    if not provider or not model:
        raise ValueError(
            f"fully_specified_name must be in 'provider/model' format, "
            f"got '{fully_specified_name}'"
        )
    if base_url:
        return init_chat_model(model, model_provider=provider, base_url=base_url)
    return init_chat_model(model, model_provider=provider)


@functools.lru_cache(maxsize=32)
def _cached_load(model_id: str, base_url: str | None) -> BaseChatModel:
    return load_chat_model(model_id, base_url=base_url)


class DynamicModel(BaseChatModel):
    """Graph-agnostic model proxy.

    Reads the target model from config.configurable at call time.
    """

    bound_tools: list[Any] = Field(default_factory=list)
    bound_kwargs: dict[str, Any] = Field(default_factory=dict)

    @property
    def _llm_type(self) -> str:
        return "dynamic"

    def _resolve(self, config: dict[str, Any] | None) -> Runnable[Any, Any]:
        cfg = (config or {}).get("configurable") or {}
        model_id: str | None = cfg.get("model") or os.environ.get("MODEL")
        if not model_id:
            raise ValueError(
                "No model configured. "
                "Set MODEL in .env or pass model via config.configurable."
            )
        base_url: str | None = cfg.get("model_base_url") or None
        real: BaseChatModel = _cached_load(model_id, base_url)
        if self.bound_tools:
            return real.bind_tools(self.bound_tools, **self.bound_kwargs)
        return real

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        **kwargs: Any,
    ) -> "DynamicModel":
        return DynamicModel(bound_tools=list(tools), bound_kwargs=dict(kwargs))

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
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
