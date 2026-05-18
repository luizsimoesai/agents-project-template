"""Configurable runtime context for the deep agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Annotated


@dataclass(kw_only=True)
class Context:
    """Runtime configuration injected into the deep agent graph."""

    model: Annotated[str, {"description": "LLM model as 'provider/model'."}] = field(
        default="",
    )
    model_base_url: Annotated[
        str | None, {"description": "Optional base URL for Ollama or proxy servers."}
    ] = field(default=None)

    def __post_init__(self) -> None:
        if env_model := os.environ.get("MODEL"):
            self.model = env_model
        if env_base_url := os.environ.get("MODEL_BASE_URL"):
            self.model_base_url = env_base_url
