"""Aegra JWT authentication handler."""

from typing import Any

from jose import JWTError, jwt
from langgraph_sdk import Auth

from src.core.settings import settings

auth = Auth()


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
    except JWTError:
        raise Auth.exceptions.HTTPException(
            status_code=401, detail="Invalid or expired token"
        )

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

    # The dict returned here is available inside graph nodes / handlers via
    # the Aegra context.  'identity' is required; other fields are optional
    # but useful for observability and authorization rules.
    return {
        "identity": user_id,
        "display_name": user_id,
        "permissions": ["authenticated"],
    }


@auth.on.assistants.create
async def set_assistant_owner(ctx: Any, value: Any) -> Any:
    """Tag assistant with owner identity for auditing."""
    if isinstance(value, dict):
        value.setdefault("metadata", {})["owner"] = ctx.user.identity
    return value


@auth.on.threads.create
async def set_thread_owner(ctx: Any, value: Any) -> Any:
    """Tag thread with owner identity for auditing."""
    if isinstance(value, dict):
        value.setdefault("metadata", {})["owner"] = ctx.user.identity
    return value
