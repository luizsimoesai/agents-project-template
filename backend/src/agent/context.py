"""Configurable runtime context for backend."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Annotated

from agent import prompts


@dataclass(kw_only=True)
class Context:
    """Runtime configuration injected into the graph."""

    system_prompt: str = field(
        default=prompts.SYSTEM_PROMPT,
        metadata={"description": "The system prompt for the agent."},
    )
    model: Annotated[str, {"description": "LLM model as 'provider/model'."}] = field(
        default="ollama/gpt-oss:120b-cloud",
    )
    model_base_url: Annotated[
        str | None, {"description": "Optional base URL for Ollama or proxy servers."}
    ] = field(default=None)

    def __post_init__(self) -> None:
        env_model = os.environ.get("MODEL")
        if env_model:
            self.model = env_model
        env_prompt = os.environ.get("SYSTEM_PROMPT")
        if env_prompt:
            self.system_prompt = env_prompt
        env_base_url = os.environ.get("MODEL_BASE_URL")
        if env_base_url:
            self.model_base_url = env_base_url
