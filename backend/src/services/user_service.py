import bcrypt
from aegra_api.core.orm import get_session
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.schemas.user import UserCreate, UserRead, UserUpdate

# bcrypt cost factor: higher = slower hash = harder to brute-force.
# OWASP recommends >= 10; 12 is a safe default (~250 ms on modern hardware).
_BCRYPT_ROUNDS = 12


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


class UserService:
    """Handles all database operations for the User entity.

    Queries are written directly in the service (no separate repository layer).
    All methods are async because we use an AsyncSession backed by asyncpg.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(self, data: UserCreate) -> UserRead:
        """Persist a new user and return its public representation.

        Hashes the plain-text password with bcrypt before storing.
        Raises 409 if a user with the same email already exists.
        """
        hashed = _hash_password(data.password)
        user = User(  # type: ignore[call-arg]
            name=data.name,
            email=data.email,
            password_hash=hashed,
        )
        self.session.add(user)
        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError:
            # The unique constraint on email was violated.
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )
        return UserRead.model_validate(user)

    async def _fetch_user(self, user_id: object) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_user(self, user_id: object) -> UserRead:
        """Fetch a user by primary key and return its public representation.

        Raises 404 if no user with that ID exists.
        """
        return UserRead.model_validate(await self._fetch_user(user_id))

    async def get_user_by_email(self, email: str) -> User | None:
        """Return the raw ORM User (including password_hash) for the given email.

        This method is intentionally internal — it is only called by AuthService
        during login so it can verify the password. Never expose it via a router.
        Returns None when no matching user exists (AuthService handles the 401).
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[UserRead]:
        """Return a paginated list of users.

        skip/limit map to SQL OFFSET/LIMIT for simple cursor-free pagination.
        """
        result = await self.session.execute(select(User).offset(skip).limit(limit))
        users = result.scalars().all()
        return [UserRead.model_validate(u) for u in users]

    async def update_user(self, user_id: object, data: UserUpdate) -> UserRead:
        """Apply a partial update (PATCH semantics) to an existing user.

        Only the fields that are explicitly provided (non-None) are written to
        the database, so the client does not need to resend unchanged values.
        Raises 404 if the user does not exist, 409 if the new email is taken.
        """
        user = await self._fetch_user(user_id)
        # model_dump(exclude_none=True) gives us only the fields the client sent.
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        try:
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )
        return UserRead.model_validate(user)

    async def set_user_active(self, user_id: object, is_active: bool) -> UserRead:
        """Toggle the is_active flag for a user.

        Called by the activate and deactivate admin endpoints.
        Raises 404 if the user does not exist.
        """
        user = await self._fetch_user(user_id)
        user.is_active = is_active
        await self.session.commit()
        await self.session.refresh(user)
        return UserRead.model_validate(user)

    async def delete_user(self, user_id: object) -> None:
        """Delete a user by primary key.

        Raises 404 if the user does not exist.
        """
        user = await self._fetch_user(user_id)
        await self.session.delete(user)
        await self.session.commit()


def get_user_service(
    session: AsyncSession = Depends(get_session),
) -> UserService:
    """FastAPI dependency factory for UserService.

    This pattern mirrors get_assistant_service from the Aegra framework:
    FastAPI resolves the AsyncSession via Depends(get_session) and passes it
    to the service constructor, keeping the service stateless and testable.
    """
    return UserService(session)
