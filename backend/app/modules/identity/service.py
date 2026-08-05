"""Identity application services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    needs_rehash,
    refresh_expiry,
    verify_password,
)
from app.modules.households.models import Household, Membership
from app.modules.identity.models import RefreshToken, User


class AuthError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def count_users(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User))
    return int(result.scalar_one())


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(func.lower(User.email) == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    timezone: str = "UTC",
    is_instance_admin: bool = False,
) -> User:
    login = email.lower().strip()
    existing = await get_user_by_email(db, login)
    if existing:
        raise AuthError("That username or email is already registered", status_code=409)

    user = User(
        email=login,
        password_hash=hash_password(password),
        display_name=display_name.strip(),
        timezone=timezone,
        is_instance_admin=is_instance_admin,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    user = await get_user_by_email(db, email.strip().lower())
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid username/email or password", status_code=401)
    if not user.is_active:
        raise AuthError("Account is disabled", status_code=403)

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        await db.flush()

    return user


async def issue_tokens(
    db: AsyncSession,
    user: User,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, str]:
    access = create_access_token(user_id=user.id, email=user.email)
    raw_refresh = generate_refresh_token()
    token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=refresh_expiry(),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(token)
    await db.flush()
    return access, raw_refresh


async def rotate_refresh_token(
    db: AsyncSession,
    raw_refresh: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, str, str]:
    token_hash = hash_token(raw_refresh)
    result = await db.execute(
        select(RefreshToken)
        .options(selectinload(RefreshToken.user))
        .where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()
    now = datetime.now(UTC)

    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise AuthError("Invalid or expired refresh token", status_code=401)

    user = stored.user
    if not user.is_active:
        raise AuthError("Account is disabled", status_code=403)

    stored.revoked_at = now
    access, new_refresh = await issue_tokens(
        db, user, user_agent=user_agent, ip_address=ip_address
    )
    return user, access, new_refresh


async def revoke_refresh_token(db: AsyncSession, raw_refresh: str | None) -> None:
    if not raw_refresh:
        return
    token_hash = hash_token(raw_refresh)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        await db.flush()


async def change_password(
    db: AsyncSession,
    user: User,
    *,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect", status_code=400)
    user.password_hash = hash_password(new_password)
    # Revoke all refresh tokens
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for token in result.scalars():
        token.revoked_at = now
    await db.flush()


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    timezone: str = "UTC",
) -> User:
    settings = get_settings()
    if settings.registration_mode == "closed":
        raise AuthError("Registration is closed", status_code=403)
    if settings.registration_mode == "invite":
        raise AuthError(
            "Registration requires an invitation. Use the invite accept flow.",
            status_code=403,
        )

    user_count = await count_users(db)
    # Prefer setup wizard when no users exist
    if user_count == 0:
        raise AuthError(
            "Instance not initialized. Use /api/v1/auth/setup first.",
            status_code=409,
        )

    return await create_user(
        db,
        email=email,
        password=password,
        display_name=display_name,
        timezone=timezone,
    )


async def setup_instance(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    household_name: str,
    timezone: str = "UTC",
    latitude: float | None = None,
    longitude: float | None = None,
) -> tuple[User, Household]:
    if await count_users(db) > 0:
        raise AuthError("Instance already initialized", status_code=410)

    user = await create_user(
        db,
        email=email,
        password=password,
        display_name=display_name,
        timezone=timezone,
        is_instance_admin=True,
    )
    household = Household(
        name=household_name.strip(),
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
        settings={},
    )
    db.add(household)
    await db.flush()

    membership = Membership(
        household_id=household.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)
    await db.flush()
    return user, household
