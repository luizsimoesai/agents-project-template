"""Aegra JWT authentication handler."""

import uuid
from typing import Any

from aegra_api.core.orm import get_session
from jose import JWTError, jwt
from langgraph_sdk import Auth
from sqlalchemy import select

from src.core.settings import settings
from src.models.user import User

auth = Auth()


async def _fetch_active_user(user_id: str) -> User | None:
    """Look up the user and return it only if it exists and is active.

    The Aegra handler runs outside FastAPI's dependency injection, so we
    iterate the get_session generator directly. The async-for ensures the
    session is closed even when we early-return from the loop body.
    """
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    async for session in get_session():
        result = await session.execute(select(User).where(User.id == uid))
        user: User | None = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        return user
    return None


def _stamp_owner(value: Any, identity: str) -> Any:
    """Mutate-in-place: ensure value['metadata']['owner'] = identity."""
    if isinstance(value, dict):
        metadata = value.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            value["metadata"] = metadata
        metadata["owner"] = identity
    return value


def _owner_filter(ctx: Any) -> dict[str, str]:
    """Return a metadata filter scoping reads to the authenticated owner.

    Aegra applies this filter to list/get/update/delete operations: only rows
    whose metadata.owner equals the caller's identity are matched.
    """
    return {"owner": ctx.user.identity}


@auth.authenticate
async def authenticate(headers: dict[str, str]) -> dict[str, object]:
    """Validate a Bearer JWT and return the user's identity for Aegra.

    Called automatically by Aegra before every request to its internal
    LangGraph endpoints. The token must be an access token (type="access")
    signed with the same secret used by our FastAPI layer.

    Returns a minimal identity dict. Aegra uses 'identity' to scope threads
    and other resources to the authenticated user.

    Raises HTTPException 401 if the token is missing, expired, invalid, or
    of the wrong type (e.g. a refresh token is rejected).
    """
    authorization = headers.get("authorization", "")
    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise Auth.exceptions.HTTPException(
            status_code=401, detail="Authorization header missing or empty"
        )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as err:
        raise Auth.exceptions.HTTPException(
            status_code=401, detail="Invalid or expired token"
        ) from err

    # Reject refresh tokens and any unknown token types — only access tokens
    # are valid for API calls.
    if payload.get("type") != "access":
        raise Auth.exceptions.HTTPException(
            status_code=401, detail="Invalid token type"
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise Auth.exceptions.HTTPException(
            status_code=401, detail="Token missing subject claim"
        )

    # Verify the user still exists and is active. Without this check, a
    # deactivated user keeps calling LangGraph endpoints with an unexpired
    # token until access_token_expire_minutes elapses — that path executes
    # the agent and its tools, so the gap is high-impact.
    user = await _fetch_active_user(user_id)
    if user is None:
        raise Auth.exceptions.HTTPException(
            status_code=401, detail="User not found or inactive"
        )

    # The dict returned here is available inside graph nodes / handlers via
    # the Aegra context.  'identity' is required; other fields are optional
    # but useful for observability and authorization rules.
    return {
        "identity": user_id,
        "display_name": user.name or user.email,
        "permissions": ["admin", "authenticated"]
        if user.is_admin
        else ["authenticated"],
    }


@auth.on.assistants.create
async def set_assistant_owner(ctx: Any, value: Any) -> Any:
    """Tag the assistant with the caller's identity on creation."""
    return _stamp_owner(value, ctx.user.identity)


@auth.on.threads.create
async def set_thread_owner(ctx: Any, value: Any) -> Any:
    """Tag the thread with the caller's identity on creation."""
    return _stamp_owner(value, ctx.user.identity)


# Without these read/search/update/delete handlers, Aegra returns rows
# regardless of who created them — any authenticated user could list every
# thread or assistant in the system. The handlers below scope every operation
# to the caller's identity by returning a metadata filter. Each Aegra action
# has its own handler type, so they cannot share a single decorated function.


@auth.on.threads.read
async def _threads_read(ctx: Any, value: Any) -> dict[str, str]:
    return _owner_filter(ctx)


@auth.on.threads.update
async def _threads_update(ctx: Any, value: Any) -> dict[str, str]:
    return _owner_filter(ctx)


@auth.on.threads.delete
async def _threads_delete(ctx: Any, value: Any) -> dict[str, str]:
    return _owner_filter(ctx)


@auth.on.threads.search
async def _threads_search(ctx: Any, value: Any) -> dict[str, str]:
    return _owner_filter(ctx)


@auth.on.assistants.read
async def _assistants_read(ctx: Any, value: Any) -> dict[str, str]:
    return _owner_filter(ctx)


@auth.on.assistants.update
async def _assistants_update(ctx: Any, value: Any) -> dict[str, str]:
    return _owner_filter(ctx)


@auth.on.assistants.delete
async def _assistants_delete(ctx: Any, value: Any) -> dict[str, str]:
    return _owner_filter(ctx)


@auth.on.assistants.search
async def _assistants_search(ctx: Any, value: Any) -> dict[str, str]:
    return _owner_filter(ctx)


@auth.on.threads.create_run
async def _threads_create_run(ctx: Any, value: Any) -> dict[str, str]:
    return _owner_filter(ctx)
