"""Basic ReAct agent."""

from langchain.agents import create_agent

from agent.basic_agent.tools import TOOLS
from agent.model import Context, configurable_model

_SYSTEM_PROMPT = """You are a helpful AI assistant."""

graph = create_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=TOOLS,
    system_prompt=_SYSTEM_PROMPT,
    context_schema=Context,
    middleware=[configurable_model],
    name="basic_agent",
)
