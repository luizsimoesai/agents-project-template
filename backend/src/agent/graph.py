"""ReAct agent with dynamic system prompt and BudgetMiddleware."""

import os
from datetime import UTC, datetime

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain_budget_middleware import BudgetMiddleware, TokenPricing

from agent.context import Context
from agent.tools import TOOLS
from agent.utils import load_chat_model


@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    """Inject system_prompt from runtime context, formatted with current UTC time."""
    return request.runtime.context.system_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )


_model = load_chat_model(os.environ.get("MODEL", "ollama/gpt-oss:120b-cloud"))

# Estimated pricing for a 120B open-source model (conservative OSS reference rates).
# Replace with actual provider pricing when known.
_pricing = TokenPricing(
    input_per_1k=0.0008,   # ~$0.80 / 1M input tokens
    output_per_1k=0.0024,  # ~$2.40 / 1M output tokens
)

graph = create_agent(
    model=_model,
    tools=TOOLS,
    context_schema=Context,
    middleware=[
        dynamic_system_prompt,
        BudgetMiddleware(
            emit_updates=True,
            scope="thread",
            token_limit=5_000,
            cost_limit=0.001,
            pricing=_pricing,
            warn_at=0.8,
            on_limit="end",
        ),
    ],
    name="agent",
)
