import uuid
from collections.abc import AsyncIterator

from aegra_api.core.orm import Thread as AegraThread
from aegra_api.core.orm import get_session
from aegra_api.core.sse import format_sse_message
from aegra_api.models.assistants import Assistant as AegraAssistant
from aegra_api.services.langgraph_service import LangGraphService, get_langgraph_service
from fastapi import Depends, HTTPException, status
from langchain_core.messages import BaseMessageChunk, HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.thread import ChatResponse, MessageRead, ThreadCreate, ThreadRead

_DEFAULT_GRAPH_ID = "agent"


def _extract_content(msg: object) -> str:
    content = getattr(msg, "content", "")
    return content if isinstance(content, str) else str(content)


def _to_read(t: AegraThread) -> ThreadRead:
    """Convert Aegra's Thread ORM to our public ThreadRead schema.

    assistant_id and thread_name are stored inside the metadata_json JSONB
    column (Aegra's convention), so we extract them with .get() to avoid
    KeyError if the dict ever lacks those keys.
    """
    meta = t.metadata_json or {}
    return ThreadRead(
        thread_id=t.thread_id,
        status=t.status,
        assistant_id=meta.get("assistant_id"),
        thread_name=meta.get("thread_name"),
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


class ThreadService:
    """Manages conversation threads and chat execution.

    Thread CRUD uses SQLAlchemy directly against Aegra's 'thread' table.
    Chat and history operations use LangGraphService to execute/read the graph
    with the PostgreSQL checkpointer that stores message history automatically.
    """

    def __init__(
        self, session: AsyncSession, langgraph_service: LangGraphService
    ) -> None:
        self.session = session
        self._lg = langgraph_service

    async def create_thread(self, data: ThreadCreate, user_id: str) -> ThreadRead:
        """Create a new conversation thread owned by user_id.

        metadata_json stores the assistant binding and optional display name so
        the chat endpoint can look them up without extra joins.
        """
        thread = AegraThread(
            thread_id=str(uuid.uuid4()),
            status="idle",
            metadata_json={
                "assistant_id": data.assistant_id,
                "graph_id": _DEFAULT_GRAPH_ID,
                "owner": user_id,
                "thread_name": data.thread_name,
            },
            user_id=user_id,
        )
        self.session.add(thread)
        await self.session.commit()
        await self.session.refresh(thread)
        return _to_read(thread)

    async def list_threads(self, user_id: str) -> list[ThreadRead]:
        """Return all threads owned by user_id."""
        result = await self.session.execute(
            select(AegraThread).where(AegraThread.user_id == user_id)
        )
        return [_to_read(t) for t in result.scalars().all()]

    async def get_thread(self, thread_id: str, user_id: str) -> ThreadRead:
        """Fetch a single thread. Raises 404 if not found or not owned by user_id."""
        thread = await self._fetch(thread_id, user_id)
        return _to_read(thread)

    async def delete_thread(self, thread_id: str, user_id: str) -> None:
        """Delete a thread and its run records.

        The thread row and associated runs are removed via Aegra's FK CASCADE.
        Note: the LangGraph checkpointer entries (message history) live in a
        separate backend table and are NOT removed by this operation — they
        remain as orphaned rows. This is the documented behaviour of Aegra's
        thread deletion: checkpoint history is intentionally kept separate.
        """
        thread = await self._fetch(thread_id, user_id)
        await self.session.delete(thread)
        await self.session.commit()

    async def chat(
        self,
        thread_id: str,
        message: str,
        assistant: AegraAssistant,
    ) -> ChatResponse:
        """Send a message and wait for the agent's reply (blocking mode).

        How it works:
        1. Build a LangGraph config that identifies the thread (for the
           checkpointer to load prior context) and applies the assistant's
           runtime settings (model, system_prompt from assistant.context).
        2. Obtain a fresh graph instance via LangGraphService — this injects
           the PostgreSQL checkpointer so message history is persisted.
        3. Invoke the graph with the user's message. The graph runs the full
           ReAct loop and returns the final state.
        4. Extract the last message from the state (the agent's reply).
        """
        # config carries only thread_id for checkpointer routing.
        # The assistant's runtime settings (model, system_prompt, etc.) are
        # passed via the context= kwarg so LangGraph coerces them into the
        # Context dataclass declared as context_schema= on the StateGraph.
        # Spreading them flat into configurable does NOT populate Runtime[T].
        config = {"configurable": {"thread_id": thread_id}}

        async with self._lg.get_graph(
            assistant.graph_id,
            config=config,
            access_context="threads.create_run",
        ) as graph:
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config,
                context=assistant.context or {},
            )

        last = result["messages"][-1]
        return ChatResponse(thread_id=thread_id, message=_extract_content(last))

    async def get_history(self, thread_id: str, user_id: str) -> list[MessageRead]:
        """Return the full conversation history for a thread.

        History is not stored in the thread table itself — it lives in the
        LangGraph checkpointer (PostgreSQL). We call graph.aget_state() to
        read the latest checkpoint, which contains all accumulated messages.
        """
        thread = await self._fetch(thread_id, user_id)  # verify ownership

        # Read the graph_id from the thread's metadata so this method works
        # correctly even if future threads are bound to a different graph.
        graph_id = (thread.metadata_json or {}).get("graph_id", _DEFAULT_GRAPH_ID)
        config = {"configurable": {"thread_id": thread_id}}

        # access_context="threads.read" tells the graph factory that we are
        # reading state (not executing), which skips execution-only setup.
        async with self._lg.get_graph(graph_id, access_context="threads.read") as graph:
            state = await graph.aget_state(config)

        messages = []
        for msg in (state.values or {}).get("messages", []):
            role = getattr(msg, "type", "unknown")
            messages.append(MessageRead(role=role, content=_extract_content(msg)))
        return messages

    async def stream_chat(
        self,
        thread_id: str,
        message: str,
        assistant: AegraAssistant,
    ) -> AsyncIterator[str]:
        """Stream the agent's reply token-by-token using the Aegra/LangGraph SSE format.

        Yields SSE-formatted strings in the following sequence:
          1. metadata        — run_id and attempt number (required by LangSmith Studio)
          2. messages/metadata — message ID and routing metadata (once per new message)
          3. messages/partial  — each token/chunk as it is generated by the LLM
          4. messages/complete — the full assembled message once streaming finishes
          5. end             — signals successful completion {"status": "success"}
          6. error           — emitted instead of 'end' if an exception occurs

        The caller wraps this generator in a FastAPI StreamingResponse with
        media_type="text/event-stream".
        """
        run_id = str(uuid.uuid4())
        # config carries only thread_id for checkpointer routing.
        # The assistant's runtime settings (model, system_prompt, etc.) are
        # passed via context= so LangGraph coerces them into Runtime[Context].
        config = {"configurable": {"thread_id": thread_id}}

        # The metadata event must be the very first thing sent — LangSmith Studio
        # and Aegra clients use run_id to correlate subsequent events.
        yield format_sse_message("metadata", {"run_id": run_id, "attempt": 1})

        # Track which message IDs we have already sent a metadata event for,
        # because messages/metadata must only be sent once per unique message.
        tracked: set[str] = set()

        try:
            async with self._lg.get_graph(
                assistant.graph_id,
                config=config,
                access_context="threads.create_run",
            ) as graph:
                # stream_mode=["messages"] yields (mode, chunk) tuples where:
                #   mode  = "messages"
                #   chunk = (BaseMessage | BaseMessageChunk, metadata_dict)
                async for mode, chunk in graph.astream(
                    {"messages": [HumanMessage(content=message)]},
                    config,
                    stream_mode=["messages"],
                    context=assistant.context or {},
                ):
                    if mode != "messages":
                        continue
                    if not isinstance(chunk, (tuple, list)) or len(chunk) != 2:  # noqa: PLR2004
                        continue

                    msg, meta = chunk
                    msg_id = getattr(msg, "id", None)

                    # Send messages/metadata once per unique message ID.
                    if msg_id and msg_id not in tracked:
                        tracked.add(msg_id)
                        yield format_sse_message(
                            "messages/metadata", {msg_id: {"metadata": meta}}
                        )

                    # BaseMessageChunk = partial/streaming token.
                    # BaseMessage (non-chunk) = complete message (e.g. ToolMessage).
                    is_partial = isinstance(msg, BaseMessageChunk)
                    event_type = (
                        "messages/partial" if is_partial else "messages/complete"
                    )
                    yield format_sse_message(event_type, [msg])

            yield format_sse_message("end", {"status": "success"})

        except Exception as exc:
            yield format_sse_message(
                "error", {"error": type(exc).__name__, "message": str(exc)}
            )

    async def _fetch(self, thread_id: str, user_id: str) -> AegraThread:
        """Internal helper: fetch a thread and verify it belongs to user_id."""
        result = await self.session.execute(
            select(AegraThread).where(
                AegraThread.thread_id == thread_id,
                AegraThread.user_id == user_id,
            )
        )
        thread = result.scalar_one_or_none()
        if thread is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found",
            )
        return thread


def get_thread_service(
    session: AsyncSession = Depends(get_session),
    langgraph_service: LangGraphService = Depends(get_langgraph_service),
) -> ThreadService:
    """FastAPI dependency factory for ThreadService.

    Follows the same Aegra pattern as get_assistant_service: FastAPI resolves
    both dependencies and passes them to the service constructor.
    """
    return ThreadService(session, langgraph_service)
