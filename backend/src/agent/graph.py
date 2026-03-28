"""ReAct agent with tool calling."""

from datetime import UTC, datetime
from typing import Literal, cast

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from agent.context import Context
from agent.state import InputState, State
from agent.tools import TOOLS
from agent.utils import load_chat_model


async def call_model(state: State, runtime: Runtime[Context]) -> dict[str, object]:
    """Invoke the model with the current messages and bound tools."""
    model = load_chat_model(runtime.context.model).bind_tools(TOOLS)
    system_message = SystemMessage(
        content=runtime.context.system_prompt.format(
            system_time=datetime.now(tz=UTC).isoformat(),
        )
    )
    response = cast(
        "AIMessage",
        await model.ainvoke([system_message, *state.messages]),
    )

    # Handle the case when it's the last step and the model still wants to use a tool
    if state.is_last_step and response.tool_calls:
        return {
            "messages": [
                AIMessage(
                    id=response.id,
                    content="Sorry, I could not find an answer to your question.",
                )
            ]
        }

    return {"messages": [response]}


def route_model_output(state: State) -> Literal["__end__", "tools"]:
    """Route based on the last message: call tools or finish."""
    if not state.messages:
        raise ValueError("Expected at least one message in State.messages")
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage):
        raise ValueError(f"Expected AIMessage, got {type(last_message).__name__}")
    if not last_message.tool_calls:
        return "__end__"
    return "tools"


graph: CompiledStateGraph = (  # type: ignore[type-arg]
    StateGraph(State, input_schema=InputState, context_schema=Context)
    .add_node("agent", call_model)
    .add_node("tools", ToolNode(TOOLS))
    .add_edge("__start__", "agent")
    .add_conditional_edges("agent", route_model_output, ["tools", "__end__"])
    .add_edge("tools", "agent")
    .compile(name="agent")
)
