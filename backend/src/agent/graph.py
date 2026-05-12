"""ReAct agent with dynamic system prompt and BudgetMiddleware."""

import os
from datetime import UTC, datetime

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt

from agent.context import Context
from agent.tools import TOOLS
from agent.utils import load_chat_model


@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    context: Context = request.runtime.context or Context()
    return str(context.system_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    ))


_model = load_chat_model(os.environ.get("MODEL", "ollama/gpt-oss:120b-cloud"))


graph = create_agent(
    model=_model,
    tools=TOOLS,
    context_schema=Context,
    middleware=[
        dynamic_system_prompt,
    ],
    name="agent",
)
