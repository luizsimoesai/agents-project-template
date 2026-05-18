"""Deep agent with planning, tool-use, and runtime model selection."""

from deepagents import create_deep_agent

from agent.deep_agent.context import Context
from agent.deep_agent.tools import TOOLS
from agent.model import configurable_model

_SYSTEM_PROMPT = """You are a helpful assistant with planning and tool-use capabilities.

You have access to tools to help answer questions:
- `get_current_time`: returns the current UTC time
- `calculator`: evaluates arithmetic expressions

Break complex tasks into steps using your built-in planning tools, then execute them."""

graph = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=TOOLS,
    system_prompt=_SYSTEM_PROMPT,
    context_schema=Context,
    middleware=[configurable_model],
    name="deep_agent",
)
