"""Deep agent with planning, tool-use, and runtime model selection."""

from deepagents import create_deep_agent

from src.agent.deep_agent.tools import TOOLS
from src.agent.model import Context, configurable_model, dynamic_system_prompt

_SYSTEM_PROMPT = """You are a helpful AI assistant."""

graph = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=TOOLS,
    system_prompt=_SYSTEM_PROMPT,
    context_schema=Context,
    middleware=[configurable_model, dynamic_system_prompt],
    name="deep_agent",
)
