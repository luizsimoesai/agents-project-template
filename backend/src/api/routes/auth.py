from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from src.core.rate_limit import limiter
from src.core.security import get_current_user
from src.core.settings import settings
from src.schemas.auth import AccessTokenResponse, LoginRequest, TokenPair
from src.schemas.user import UserCreate, UserRead
from src.services.auth_service import AuthService, get_auth_service
from src.services.user_service import UserService, get_user_service

# All auth endpoints are public (no JWT required).
# The tag groups these endpoints together in the OpenAPI /docs UI.
router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE_NAME = "refresh_token"
# Cookie is scoped to /api/v1/auth so it only travels to /refresh and /logout,
# minimizing exposure to other endpoints that don't need it.
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=_REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_REFRESH_COOKIE_NAME,
        path=_REFRESH_COOKIE_PATH,
    )


def _to_response(pair: TokenPair) -> AccessTokenResponse:
    return AccessTokenResponse(
        access_token=pair.access_token, expires_in=pair.expires_in
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(
    request: Request,
    data: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    """Create a new account and return the public user representation.

    The plain-text password is hashed by UserService before being stored —
    it is never persisted or returned. Rate-limited to deter signup spam.
    """
    return await user_service.create_user(data)


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AccessTokenResponse:
    """Authenticate with email + password and issue tokens.

    The refresh token is delivered as an HttpOnly cookie scoped to
    /api/v1/auth — JS code cannot read it. The body returns the access
    token (used by the JS client for Bearer auth) and expires_in.
    Same generic error for wrong email or wrong password to prevent
    enumeration. Rate-limited to slow online brute-force.
    """
    pair = await auth_service.login(data)
    _set_refresh_cookie(response, pair.refresh_token)
    return _to_response(pair)


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie(alias=_REFRESH_COOKIE_NAME)] = None,
) -> AccessTokenResponse:
    """Rotate the token pair. Reads the refresh token from its HttpOnly cookie.

    Each call invalidates the previous refresh token's jti and issues a fresh
    pair. The new refresh token is set as a cookie; the access token is
    returned in the body.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    pair = await auth_service.refresh(refresh_token)
    _set_refresh_cookie(response, pair.refresh_token)
    return _to_response(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie(alias=_REFRESH_COOKIE_NAME)] = None,
) -> None:
    """Invalidate the current refresh token server-side and clear the cookie.

    Idempotent: returns 204 even if no cookie is present or the token has
    already expired. Does not require a Bearer token — logging out should
    work even when the access token is expired.
    """
    await auth_service.logout(refresh_token)
    _clear_refresh_cookie(response)


@router.get("/me")
async def me(
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> UserRead:
    """Return the profile of the currently authenticated user.

    The token is validated by get_current_user; if the token is missing,
    expired, or invalid a 401 is returned automatically.
    """
    return current_user
