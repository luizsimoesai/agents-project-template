"""Aegra JWT authentication handler.

This module registers a @auth.authenticate handler that validates the same
Bearer JWT tokens issued by our FastAPI /auth/login endpoint.  Registering
this handler in aegra.json makes Aegra's *internal* LangGraph endpoints
(/threads, /runs, /assistants, etc.) require the same tokens, so all traffic
through the platform is secured with a single, unified auth scheme.

How it integrates:
  aegra.json  →  "auth": {"path": "./src/auth/jwt.py:auth"}
  Aegra calls authenticate() on every request to its internal endpoints.
  Custom FastAPI routes (/api/v1/…) still use our get_current_user dependency.
"""

from jose import JWTError, jwt
from langgraph_sdk import Auth

from src.core.settings import settings

# The auth object is what Aegra imports; the @auth.authenticate decorator
# registers our handler so Aegra knows which function to call.
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
async def set_assistant_owner(ctx, value):
    """Tag the assistant with the owner's identity for observability.

    Aegra already scopes all resources to the authenticated user via 'identity',
    so this metadata is supplementary — useful for admin queries and auditing.
    """
    if isinstance(value, dict):
        value.setdefault("metadata", {})["owner"] = ctx.user.identity
    return value


@auth.on.threads.create
async def set_thread_owner(ctx, value):
    """Tag the thread with the owner's identity for observability.

    Aegra already scopes all resources to the authenticated user via 'identity',
    so this metadata is supplementary — useful for admin queries and auditing.
    """
    if isinstance(value, dict):
        value.setdefault("metadata", {})["owner"] = ctx.user.identity
    return value
