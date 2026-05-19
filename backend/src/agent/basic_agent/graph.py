"""Basic ReAct agent."""

from langchain.agents import create_agent

from src.agent.basic_agent.tools import TOOLS
from src.agent.model import Context, configurable_model, dynamic_system_prompt

_SYSTEM_PROMPT = """You are a helpful AI assistant."""

graph = create_agent(  # type: ignore[misc]
    # mypy can't unify ContextT here: the wrap_model_call-decorated middlewares
    # are typed as AgentMiddleware[Any, Any], conflicting with context_schema=Context.
    model="anthropic:claude-sonnet-4-6",
    tools=TOOLS,
    system_prompt=_SYSTEM_PROMPT,
    context_schema=Context,
    middleware=[configurable_model, dynamic_system_prompt],
    name="basic_agent",
)
