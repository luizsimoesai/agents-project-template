from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.security import get_current_user
from src.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from src.schemas.user import UserCreate, UserRead
from src.services.auth_service import AuthService, get_auth_service
from src.services.user_service import UserService, get_user_service

# All auth endpoints are public (no JWT required).
# The tag groups these endpoints together in the OpenAPI /docs UI.
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    """Create a new account and return the public user representation.

    The plain-text password is hashed by UserService before being stored —
    it is never persisted or returned.
    """
    return await user_service.create_user(data)


@router.post("/login")
async def login(
    data: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate with email + password and receive a JWT token pair.

    Returns the same generic error for wrong email OR wrong password so that
    an attacker cannot determine which field is incorrect.
    """
    return await auth_service.login(data)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Exchange a valid refresh token for a new access + refresh token pair.

    Token rotation: each call discards the previous refresh token and issues
    fresh ones. Using an access token here will return 401.
    """
    return await auth_service.refresh(body.refresh_token)


@router.get("/me")
async def me(
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> UserRead:
    """Return the profile of the currently authenticated user.

    The token is validated by get_current_user; if the token is missing,
    expired, or invalid a 401 is returned automatically.
    """
    return current_user
