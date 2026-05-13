"""ReAct agent with dynamic system prompt."""

from datetime import UTC, datetime

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt

from agent.context import Context
from agent.tools import TOOLS
from agent.utils import DYNAMIC_MODEL


@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    context: Context = request.runtime.context or Context()
    return str(
        context.system_prompt.format(system_time=datetime.now(tz=UTC).isoformat())
    )


graph = create_agent(
    model=DYNAMIC_MODEL,
    tools=TOOLS,
    context_schema=Context,
    middleware=[dynamic_system_prompt],
    name="agent",
)
