"""DeepAgent example using the deepagents quickstart pattern."""

import os

from deepagents import create_deep_agent

from agent.deepagents.tools import TOOLS
from agent.utils import load_chat_model

_model = load_chat_model(os.environ.get("MODEL", "ollama/gpt-oss:120b-cloud"))

_SYSTEM_PROMPT = """You are a helpful assistant with planning and tool-use capabilities.

You have access to tools to help answer questions:
- `get_current_time`: returns the current UTC time
- `calculator`: evaluates arithmetic expressions

Break complex tasks into steps using your built-in planning tools, then execute them."""

graph = create_deep_agent(
    model=_model,
    tools=TOOLS,
    system_prompt=_SYSTEM_PROMPT,
    name="deep_agent",
)
