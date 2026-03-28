from datetime import datetime
from typing import Any

from pydantic import BaseModel


# AssistantCreate is the request body for creating a new assistant.
# graph_id defaults to "agent" — the only graph registered in aegra.json.
# config and context are passed to the LangGraph runtime at execution time:
#   - config: low-level LangGraph configuration (e.g. recursion limits)
#   - context: runtime context consumed by src/agent/context.py
#              (e.g. {"model": "anthropic/claude-sonnet-4-6", "system_prompt": "..."})
# metadata: arbitrary key-value pairs useful for searching/filtering assistants.
class AssistantCreate(BaseModel):
    name: str
    description: str | None = None
    graph_id: str = "agent"
    config: dict[str, Any] = {}
    context: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


# AssistantRead is the public representation of an assistant.
# user_id is intentionally omitted — it is an internal scoping field and
# clients already know their own identity from the JWT.
class AssistantRead(BaseModel):
    assistant_id: str
    name: str
    description: str | None
    graph_id: str
    config: dict[str, Any]
    context: dict[str, Any]
    metadata: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime


# AssistantUpdate uses fully optional fields (PATCH semantics).
# Only the fields explicitly sent by the client will be forwarded to the Aegra service.
class AssistantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
