from datetime import datetime
from typing import Literal

from pydantic import BaseModel


# ThreadCreate is the request body for starting a new conversation.
# Every thread must be tied to an assistant — the assistant's context
# (model, system_prompt) will be applied to every run executed in it.
class ThreadCreate(BaseModel):
    assistant_id: str
    thread_name: str | None = None


# ThreadRead is the public representation of a thread.
# assistant_id and thread_name are stored inside metadata_json in the Aegra
# table; we extract them here for a cleaner API surface.
class ThreadRead(BaseModel):
    thread_id: str
    status: Literal["idle", "busy", "interrupted", "error"]
    assistant_id: str | None
    thread_name: str | None
    created_at: datetime
    updated_at: datetime


# ChatRequest carries the user's plain-text message.
# The service layer converts it to a LangChain HumanMessage before invoking
# the graph so the caller does not need to know about LangChain internals.
class ChatRequest(BaseModel):
    message: str


# ChatResponse returns the agent's reply and the thread_id so the client can
# continue the conversation by sending another ChatRequest to the same thread.
class ChatResponse(BaseModel):
    thread_id: str
    message: str
    role: str = "assistant"


# MessageRead is one entry in the conversation history.
# role maps to LangChain message types: "human", "ai", "tool".
class MessageRead(BaseModel):
    role: str
    content: str
