"""Household application services."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_token
from app.modules.households.models import Household, Invitation, Membership
from app.modules.households.permissions import (
    can_manage_members,
    is_valid_role,
    role_at_least,
)
from app.modules.identity.models import User


class HouseholdError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def list_households_for_user(
    db: AsyncSession, user_id: uuid.UUID
) -> list[tuple[Household, str]]:
    result = await db.execute(
        select(Household, Membership.role)
        .join(Membership, Membership.household_id == Household.id)
        .where(Membership.user_id == user_id)
        .order_by(Household.name)
    )
    return list(result.all())


async def get_membership(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Membership | None:
    result = await db.execute(
        select(Membership)
        .options(selectinload(Membership.household), selectinload(Membership.user))
        .where(
            Membership.household_id == household_id,
            Membership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_household(db: AsyncSession, household_id: uuid.UUID) -> Household | None:
    result = await db.execute(select(Household).where(Household.id == household_id))
    return result.scalar_one_or_none()


async def create_household(
    db: AsyncSession,
    *,
    owner: User,
    name: str,
    timezone: str = "UTC",
    currency: str = "USD",
    latitude: float | None = None,
    longitude: float | None = None,
) -> Household:
    household = Household(
        name=name.strip(),
        timezone=timezone,
        currency=currency.upper(),
        latitude=latitude,
        longitude=longitude,
        settings={},
    )
    db.add(household)
    await db.flush()
    db.add(
        Membership(
            household_id=household.id,
            user_id=owner.id,
            role="owner",
        )
    )
    await db.flush()
    return household


async def update_household(
    db: AsyncSession,
    household: Household,
    *,
    name: str | None = None,
    timezone: str | None = None,
    currency: str | None = None,
    latitude: float | None = ...,  # type: ignore[assignment]
    longitude: float | None = ...,  # type: ignore[assignment]
    settings: dict | None = None,
) -> Household:
    if name is not None:
        household.name = name.strip()
    if timezone is not None:
        household.timezone = timezone
    if currency is not None:
        household.currency = currency.upper()
    if latitude is not ...:
        household.latitude = latitude
    if longitude is not ...:
        household.longitude = longitude
    if settings is not None:
        household.settings = settings
    await db.flush()
    return household


async def delete_household(db: AsyncSession, household: Household) -> None:
    await db.delete(household)
    await db.flush()


async def list_members(db: AsyncSession, household_id: uuid.UUID) -> list[Membership]:
    result = await db.execute(
        select(Membership)
        .options(selectinload(Membership.user))
        .where(Membership.household_id == household_id)
        .order_by(Membership.created_at)
    )
    return list(result.scalars())


async def count_owners(db: AsyncSession, household_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Membership)
        .where(Membership.household_id == household_id, Membership.role == "owner")
    )
    return int(result.scalar_one())


async def update_member_role(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    target_user_id: uuid.UUID,
    new_role: str,
    actor_role: str,
) -> Membership:
    if not is_valid_role(new_role) or new_role == "owner" and actor_role != "owner":
        if new_role == "owner" and actor_role != "owner":
            raise HouseholdError("Only an owner can grant ownership", status_code=403)
        if not is_valid_role(new_role):
            raise HouseholdError("Invalid role", status_code=400)

    if not can_manage_members(actor_role):
        raise HouseholdError("Insufficient permissions", status_code=403)

    membership = await get_membership(db, household_id=household_id, user_id=target_user_id)
    if membership is None:
        raise HouseholdError("Member not found", status_code=404)

    # Admins cannot modify owners or other admins above them
    if membership.role == "owner" and actor_role != "owner":
        raise HouseholdError("Cannot modify an owner", status_code=403)
    if actor_role == "admin" and role_at_least(membership.role, "admin"):
        raise HouseholdError("Admins cannot modify other admins or owners", status_code=403)

    if (
        membership.role == "owner"
        and new_role != "owner"
        and await count_owners(db, household_id) <= 1
    ):
        raise HouseholdError("Cannot demote the last owner", status_code=400)

    membership.role = new_role
    await db.flush()
    return membership


async def remove_member(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    target_user_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    actor_role: str,
) -> None:
    membership = await get_membership(db, household_id=household_id, user_id=target_user_id)
    if membership is None:
        raise HouseholdError("Member not found", status_code=404)

    leaving_self = target_user_id == actor_user_id
    if not leaving_self and not can_manage_members(actor_role):
        raise HouseholdError("Insufficient permissions", status_code=403)

    if membership.role == "owner":
        if await count_owners(db, household_id) <= 1:
            raise HouseholdError(
                "Cannot remove the last owner. Transfer ownership or delete the household.",
                status_code=400,
            )
        if not leaving_self and actor_role != "owner":
            raise HouseholdError("Only an owner can remove another owner", status_code=403)

    if not leaving_self and actor_role == "admin" and role_at_least(membership.role, "admin"):
        raise HouseholdError("Admins cannot remove other admins or owners", status_code=403)

    await db.delete(membership)
    await db.flush()


async def create_invitation(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    invited_by: User,
    email: str | None,
    role: str,
    expires_in_days: int = 7,
) -> tuple[Invitation, str]:
    if not is_valid_role(role) or role == "owner":
        raise HouseholdError("Invitations cannot grant owner role", status_code=400)

    raw = secrets.token_urlsafe(32)
    invitation = Invitation(
        household_id=household_id,
        email=email.lower().strip() if email else None,
        role=role,
        token_hash=hash_token(raw),
        invited_by_user_id=invited_by.id,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
    )
    db.add(invitation)
    await db.flush()
    return invitation, raw


async def list_invitations(db: AsyncSession, household_id: uuid.UUID) -> list[Invitation]:
    result = await db.execute(
        select(Invitation)
        .where(Invitation.household_id == household_id)
        .order_by(Invitation.created_at.desc())
    )
    return list(result.scalars())


async def revoke_invitation(
    db: AsyncSession, household_id: uuid.UUID, invitation_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.household_id == household_id,
        )
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HouseholdError("Invitation not found", status_code=404)
    await db.delete(invitation)
    await db.flush()


async def accept_invitation(db: AsyncSession, *, user: User, raw_token: str) -> Membership:
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(Invitation)
        .options(selectinload(Invitation.household))
        .where(Invitation.token_hash == token_hash)
    )
    invitation = result.scalar_one_or_none()
    now = datetime.now(UTC)

    if invitation is None:
        raise HouseholdError("Invalid invitation", status_code=404)
    if invitation.accepted_at is not None:
        raise HouseholdError("Invitation already used", status_code=409)
    if invitation.expires_at < now:
        raise HouseholdError("Invitation expired", status_code=410)
    if invitation.email and invitation.email.lower() != user.email.lower():
        raise HouseholdError("Invitation is for a different email address", status_code=403)

    existing = await get_membership(
        db, household_id=invitation.household_id, user_id=user.id
    )
    if existing:
        invitation.accepted_at = now
        await db.flush()
        return existing

    membership = Membership(
        household_id=invitation.household_id,
        user_id=user.id,
        role=invitation.role,
    )
    db.add(membership)
    invitation.accepted_at = now
    await db.flush()
    return membership
