"""Shared FastAPI dependencies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.households.models import Household, Membership
from app.modules.households.permissions import role_at_least
from app.modules.households.service import get_membership
from app.modules.identity.models import User
from app.modules.identity.service import get_user_by_id

DbSession = Annotated[AsyncSession, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> User:
    token: str | None = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass
class HouseholdContext:
    household: Household
    membership: Membership
    user: User

    @property
    def role(self) -> str:
        return self.membership.role


def require_household_role(minimum_role: str):
    async def _dependency(
        household_id: uuid.UUID,
        db: DbSession,
        user: CurrentUser,
    ) -> HouseholdContext:
        membership = await get_membership(
            db, household_id=household_id, user_id=user.id
        )
        # 404 hides existence across tenants
        if membership is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")
        if not role_at_least(membership.role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return HouseholdContext(
            household=membership.household,
            membership=membership,
            user=user,
        )

    return _dependency


def client_meta(
    user_agent: Annotated[str | None, Header()] = None,
    x_forwarded_for: Annotated[str | None, Header()] = None,
) -> tuple[str | None, str | None]:
    ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None
    return user_agent, ip
