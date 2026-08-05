"""Household and membership routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DbSession, HouseholdContext, require_household_role
from app.modules.households import service as household_service
from app.modules.households.schemas import (
    AcceptInvitationRequest,
    HouseholdCreate,
    HouseholdPublic,
    HouseholdUpdate,
    InvitationCreate,
    InvitationPublic,
    MemberPublic,
    MemberRoleUpdate,
)
from app.modules.households.service import HouseholdError

router = APIRouter(prefix="/api/v1", tags=["households"])


def _hh_error(exc: HouseholdError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("/households", response_model=list[HouseholdPublic])
async def list_households(user: CurrentUser, db: DbSession) -> list[HouseholdPublic]:
    rows = await household_service.list_households_for_user(db, user.id)
    return [
        HouseholdPublic(
            id=h.id,
            name=h.name,
            slug=h.slug,
            timezone=h.timezone,
            currency=h.currency,
            latitude=h.latitude,
            longitude=h.longitude,
            settings=h.settings or {},
            role=role,  # type: ignore[arg-type]
            created_at=h.created_at,
        )
        for h, role in rows
    ]


@router.post("/households", response_model=HouseholdPublic, status_code=status.HTTP_201_CREATED)
async def create_household(
    body: HouseholdCreate,
    user: CurrentUser,
    db: DbSession,
) -> HouseholdPublic:
    household = await household_service.create_household(
        db,
        owner=user,
        name=body.name,
        timezone=body.timezone,
        currency=body.currency,
        latitude=body.latitude,
        longitude=body.longitude,
    )
    await db.commit()
    await db.refresh(household)
    return HouseholdPublic(
        id=household.id,
        name=household.name,
        slug=household.slug,
        timezone=household.timezone,
        currency=household.currency,
        latitude=household.latitude,
        longitude=household.longitude,
        settings=household.settings or {},
        role="owner",
        created_at=household.created_at,
    )


@router.get("/households/{household_id}", response_model=HouseholdPublic)
async def get_household(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
) -> HouseholdPublic:
    h = ctx.household
    return HouseholdPublic(
        id=h.id,
        name=h.name,
        slug=h.slug,
        timezone=h.timezone,
        currency=h.currency,
        latitude=h.latitude,
        longitude=h.longitude,
        settings=h.settings or {},
        role=ctx.role,  # type: ignore[arg-type]
        created_at=h.created_at,
    )


@router.patch("/households/{household_id}", response_model=HouseholdPublic)
async def update_household(
    body: HouseholdUpdate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("owner"))],
    db: DbSession,
) -> HouseholdPublic:
    data = body.model_dump(exclude_unset=True)
    # Merge convenience flags into settings JSON
    settings = dict(ctx.household.settings or {})
    if "settings" in data and isinstance(data["settings"], dict):
        settings.update(data.pop("settings"))
    if "auto_cover_images" in data:
        settings["auto_cover_images"] = data.pop("auto_cover_images")
    if "plantnet_api_key" in data:
        key = data.pop("plantnet_api_key")
        if key is None or key == "":
            settings.pop("plantnet_api_key", None)
        else:
            settings["plantnet_api_key"] = key
    if "weather_provider" in data:
        wp = data.pop("weather_provider")
        if wp:
            settings["weather_provider"] = wp
    if "plant_id_provider" in data:
        pip = data.pop("plant_id_provider")
        if pip:
            settings["plant_id_provider"] = pip
    kwargs: dict = {k: v for k, v in data.items() if k not in ("latitude", "longitude")}
    if "latitude" in data:
        kwargs["latitude"] = data["latitude"]
    if "longitude" in data:
        kwargs["longitude"] = data["longitude"]
    kwargs["settings"] = settings

    household = await household_service.update_household(db, ctx.household, **kwargs)
    await db.commit()
    await db.refresh(household)
    return HouseholdPublic(
        id=household.id,
        name=household.name,
        slug=household.slug,
        timezone=household.timezone,
        currency=household.currency,
        latitude=household.latitude,
        longitude=household.longitude,
        settings=household.settings or {},
        role="owner",
        created_at=household.created_at,
    )


@router.delete("/households/{household_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_household(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("owner"))],
    db: DbSession,
) -> None:
    await household_service.delete_household(db, ctx.household)
    await db.commit()


@router.get("/households/{household_id}/members", response_model=list[MemberPublic])
async def list_members(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> list[MemberPublic]:
    members = await household_service.list_members(db, ctx.household.id)
    return [
        MemberPublic(
            user_id=m.user_id,
            email=m.user.email,
            display_name=m.user.display_name,
            role=m.role,  # type: ignore[arg-type]
            joined_at=m.created_at,
        )
        for m in members
    ]


@router.patch(
    "/households/{household_id}/members/{user_id}",
    response_model=MemberPublic,
)
async def update_member(
    user_id: uuid.UUID,
    body: MemberRoleUpdate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("admin"))],
    db: DbSession,
) -> MemberPublic:
    try:
        membership = await household_service.update_member_role(
            db,
            household_id=ctx.household.id,
            target_user_id=user_id,
            new_role=body.role,
            actor_role=ctx.role,
        )
        await db.commit()
        # reload user
        membership = await household_service.get_membership(
            db, household_id=ctx.household.id, user_id=user_id
        )
        assert membership is not None
    except HouseholdError as exc:
        await db.rollback()
        raise _hh_error(exc) from exc

    return MemberPublic(
        user_id=membership.user_id,
        email=membership.user.email,
        display_name=membership.user.display_name,
        role=membership.role,  # type: ignore[arg-type]
        joined_at=membership.created_at,
    )


@router.delete(
    "/households/{household_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    user_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> None:
    # Self-leave allowed for any member; others need admin (checked in service)
    try:
        await household_service.remove_member(
            db,
            household_id=ctx.household.id,
            target_user_id=user_id,
            actor_user_id=ctx.user.id,
            actor_role=ctx.role,
        )
        await db.commit()
    except HouseholdError as exc:
        await db.rollback()
        raise _hh_error(exc) from exc


@router.post(
    "/households/{household_id}/invitations",
    response_model=InvitationPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    body: InvitationCreate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("admin"))],
    db: DbSession,
) -> InvitationPublic:
    try:
        invitation, raw = await household_service.create_invitation(
            db,
            household_id=ctx.household.id,
            invited_by=ctx.user,
            email=body.email,
            role=body.role,
            expires_in_days=body.expires_in_days,
        )
        await db.commit()
        await db.refresh(invitation)
    except HouseholdError as exc:
        await db.rollback()
        raise _hh_error(exc) from exc

    return InvitationPublic(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,  # type: ignore[arg-type]
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        created_at=invitation.created_at,
        token=raw,
        invite_url_path=f"/invite/{raw}",
    )


@router.get(
    "/households/{household_id}/invitations",
    response_model=list[InvitationPublic],
)
async def list_invitations(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("admin"))],
    db: DbSession,
) -> list[InvitationPublic]:
    invitations = await household_service.list_invitations(db, ctx.household.id)
    return [
        InvitationPublic(
            id=i.id,
            email=i.email,
            role=i.role,  # type: ignore[arg-type]
            expires_at=i.expires_at,
            accepted_at=i.accepted_at,
            created_at=i.created_at,
        )
        for i in invitations
    ]


@router.delete(
    "/households/{household_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("admin"))],
    db: DbSession,
) -> None:
    try:
        await household_service.revoke_invitation(db, ctx.household.id, invitation_id)
        await db.commit()
    except HouseholdError as exc:
        await db.rollback()
        raise _hh_error(exc) from exc


@router.post("/invitations/accept", response_model=HouseholdPublic)
async def accept_invitation(
    body: AcceptInvitationRequest,
    user: CurrentUser,
    db: DbSession,
) -> HouseholdPublic:
    try:
        membership = await household_service.accept_invitation(
            db, user=user, raw_token=body.token
        )
        await db.commit()
        membership = await household_service.get_membership(
            db, household_id=membership.household_id, user_id=user.id
        )
        assert membership is not None
    except HouseholdError as exc:
        await db.rollback()
        raise _hh_error(exc) from exc

    h = membership.household
    return HouseholdPublic(
        id=h.id,
        name=h.name,
        slug=h.slug,
        timezone=h.timezone,
        currency=h.currency,
        latitude=h.latitude,
        longitude=h.longitude,
        settings=h.settings or {},
        role=membership.role,  # type: ignore[arg-type]
        created_at=h.created_at,
    )
