"""Layout, weather, stats, calendar, and label routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, HouseholdContext, require_household_role
from app.modules.labels.service import build_labels_pdf
from app.modules.layout import service as layout_service
from app.modules.layout.models import Placement
from app.modules.layout.service import LayoutError
from app.modules.plants.models import Plant
from app.modules.stats import service as stats_service
from app.modules.weather import service as weather_service

router = APIRouter(prefix="/api/v1", tags=["extras"])


def _layout_err(exc: LayoutError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


# --- Schemas ---


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    latitude: float | None = None
    longitude: float | None = None
    # Create a first area so the layout map is usable immediately.
    default_room: str | None = Field(default="Garden")
    default_kind: str = "garden"
    length_m: float | None = None
    width_m: float | None = None


class SpaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: str = "garden"
    canvas_width: int = 1000
    canvas_height: int = 800
    length_m: float | None = Field(default=None, gt=0, le=500)
    width_m: float | None = Field(default=None, gt=0, le=500)
    notes: str | None = None


class SpaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: str | None = None
    length_m: float | None = Field(default=None, ge=0, le=500)
    width_m: float | None = Field(default=None, ge=0, le=500)
    notes: str | None = None
    canvas_width: int | None = Field(default=None, ge=100, le=4000)
    canvas_height: int | None = Field(default=None, ge=100, le=4000)


class ContainerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    # circle | square | rect | triangle | line | polygon
    kind: str | None = "circle"
    x: float = 0
    y: float = 0
    width: float | None = 56
    height: float | None = 56
    path_json: list[list[float]] | None = None
    emoji: str | None = Field(default=None, max_length=16)


class ContainerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: str | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = Field(default=None, ge=8, le=800)
    height: float | None = Field(default=None, ge=8, le=800)
    path_json: list[list[float]] | None = None
    emoji: str | None = Field(default=None, max_length=16)


class PlacementUpsert(BaseModel):
    space_id: uuid.UUID
    container_id: uuid.UUID | None = None
    x: float = 0
    y: float = 0
    width: float | None = 64
    height: float | None = 64


class LabelsRequest(BaseModel):
    plant_ids: list[uuid.UUID] = Field(min_length=1)


# --- Demo ---


@router.post("/households/{household_id}/demo/seed")
async def seed_demo(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
    auto_cover: bool = Query(False, description="Fetch Wikimedia covers (slow)"),
) -> dict[str, Any]:
    """Create a sample garden map + plants for exploration.

    Fast by default (no photo downloads). Set auto_cover=true to try covers.
    """
    from app.modules.demo.seed import seed_demo_garden

    try:
        result = await seed_demo_garden(
            db,
            household_id=ctx.household.id,
            user_id=ctx.user.id,
            auto_cover=auto_cover,
        )
        await db.commit()
        return result
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Demo seed failed: {exc}") from exc


@router.delete("/households/{household_id}/demo")
async def clear_demo(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    """Remove the demo garden site and plants tagged demo."""
    from app.modules.demo.seed import clear_demo_garden

    try:
        result = await clear_demo_garden(db, household_id=ctx.household.id)
        await db.commit()
        return result
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Clear demo failed: {exc}") from exc


# --- Weather ---


@router.get("/households/{household_id}/weather")
async def get_weather(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> dict[str, Any]:
    snap = await weather_service.get_household_weather(db, ctx.household)
    await db.commit()
    data = weather_service.weather_public(snap)
    if data is None:
        return {
            "configured": False,
            "message": "Set household latitude/longitude in settings to enable weather.",
        }
    return {"configured": True, **data}


@router.post("/households/{household_id}/weather/refresh")
async def refresh_weather(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    snap = await weather_service.get_household_weather(db, ctx.household, force=True)
    await db.commit()
    data = weather_service.weather_public(snap)
    if data is None:
        raise HTTPException(
            status_code=400,
            detail="Set household coordinates first (latitude/longitude).",
        )
    return {"configured": True, **data}


# --- Layout ---


@router.get("/households/{household_id}/sites")
async def list_sites(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> list[dict[str, Any]]:
    sites = await layout_service.list_sites(db, ctx.household.id)
    out = []
    for site in sites:
        out.append(
            {
                "id": str(site.id),
                "name": site.name,
                "latitude": site.latitude,
                "longitude": site.longitude,
                "sort_order": site.sort_order,
                "spaces": [
                    {
                        "id": str(sp.id),
                        "name": sp.name,
                        "kind": sp.kind,
                        "canvas_width": sp.canvas_width,
                        "canvas_height": sp.canvas_height,
                        "length_m": sp.length_m,
                        "width_m": sp.width_m,
                        "notes": sp.notes,
                        "sort_order": sp.sort_order,
                        "containers": [
                            {
                                "id": str(c.id),
                                "name": c.name,
                                "kind": c.kind,
                                "emoji": c.emoji,
                                "x": c.x,
                                "y": c.y,
                                "width": c.width,
                                "height": c.height,
                                "path_json": c.path_json or [],
                            }
                            for c in sp.containers
                        ],
                        "placements": [
                            {
                                "id": str(p.id),
                                "plant_id": str(p.plant_id),
                                "container_id": str(p.container_id) if p.container_id else None,
                                "x": p.x,
                                "y": p.y,
                                "width": p.width,
                                "height": p.height,
                            }
                            for p in sp.placements
                        ],
                    }
                    for sp in site.spaces
                ],
            }
        )
    return out


@router.post(
    "/households/{household_id}/sites",
    status_code=status.HTTP_201_CREATED,
)
async def create_site(
    body: SiteCreate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    try:
        site = await layout_service.create_site(
            db,
            household_id=ctx.household.id,
            name=body.name,
            latitude=body.latitude,
            longitude=body.longitude,
        )
        space = None
        room_name = (body.default_room or "").strip()
        if room_name:
            space = await layout_service.create_space(
                db,
                household_id=ctx.household.id,
                site_id=site.id,
                name=room_name,
                kind=body.default_kind or "garden",
                length_m=body.length_m,
                width_m=body.width_m,
            )
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc
    return {
        "id": str(site.id),
        "name": site.name,
        "space_id": str(space.id) if space else None,
        "space_name": space.name if space else None,
    }


@router.post(
    "/households/{household_id}/sites/{site_id}/spaces",
    status_code=status.HTTP_201_CREATED,
)
async def create_space(
    site_id: uuid.UUID,
    body: SpaceCreate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    try:
        space = await layout_service.create_space(
            db,
            household_id=ctx.household.id,
            site_id=site_id,
            name=body.name,
            kind=body.kind,
            canvas_width=body.canvas_width,
            canvas_height=body.canvas_height,
            length_m=body.length_m,
            width_m=body.width_m,
            notes=body.notes,
        )
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc
    return {
        "id": str(space.id),
        "name": space.name,
        "kind": space.kind,
        "length_m": space.length_m,
        "width_m": space.width_m,
        "canvas_width": space.canvas_width,
        "canvas_height": space.canvas_height,
    }


@router.patch("/households/{household_id}/spaces/{space_id}")
async def update_space(
    space_id: uuid.UUID,
    body: SpaceUpdate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    try:
        space = await layout_service.update_space(
            db,
            household_id=ctx.household.id,
            space_id=space_id,
            **body.model_dump(exclude_unset=True),
        )
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc
    return {
        "id": str(space.id),
        "name": space.name,
        "kind": space.kind,
        "length_m": space.length_m,
        "width_m": space.width_m,
        "canvas_width": space.canvas_width,
        "canvas_height": space.canvas_height,
        "notes": space.notes,
    }


@router.delete(
    "/households/{household_id}/spaces/{space_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_space(
    space_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> None:
    """Delete a room or garden area (and its pots). Plants stay in your collection."""
    try:
        await layout_service.delete_space(
            db, household_id=ctx.household.id, space_id=space_id
        )
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc


@router.post(
    "/households/{household_id}/spaces/{space_id}/containers",
    status_code=status.HTTP_201_CREATED,
)
async def create_container(
    space_id: uuid.UUID,
    body: ContainerCreate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    try:
        c = await layout_service.create_container(
            db,
            household_id=ctx.household.id,
            space_id=space_id,
            name=body.name,
            kind=body.kind,
            x=body.x,
            y=body.y,
            width=body.width,
            height=body.height,
            path_json=body.path_json,
            emoji=body.emoji,
        )
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc
    return {
        "id": str(c.id),
        "name": c.name,
        "kind": c.kind,
        "emoji": c.emoji,
        "x": c.x,
        "y": c.y,
        "width": c.width,
        "height": c.height,
        "path_json": c.path_json or [],
    }


@router.patch("/households/{household_id}/containers/{container_id}")
async def update_container(
    container_id: uuid.UUID,
    body: ContainerUpdate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    try:
        c = await layout_service.update_container(
            db,
            household_id=ctx.household.id,
            container_id=container_id,
            **body.model_dump(exclude_unset=True),
        )
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc
    return {
        "id": str(c.id),
        "name": c.name,
        "kind": c.kind,
        "emoji": c.emoji,
        "x": c.x,
        "y": c.y,
        "width": c.width,
        "height": c.height,
        "path_json": c.path_json or [],
    }


@router.delete(
    "/households/{household_id}/containers/{container_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_container(
    container_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> None:
    try:
        await layout_service.delete_container(
            db, household_id=ctx.household.id, container_id=container_id
        )
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc


@router.post(
    "/households/{household_id}/containers/{container_id}/copy",
    status_code=status.HTTP_201_CREATED,
)
async def copy_container(
    container_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    try:
        c = await layout_service.duplicate_container(
            db, household_id=ctx.household.id, container_id=container_id
        )
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc
    return {
        "id": str(c.id),
        "name": c.name,
        "kind": c.kind,
        "x": c.x,
        "y": c.y,
        "width": c.width,
        "height": c.height,
    }


@router.put("/households/{household_id}/plants/{plant_id}/placement")
async def put_placement(
    plant_id: uuid.UUID,
    body: PlacementUpsert,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    try:
        p = await layout_service.upsert_placement(
            db,
            household_id=ctx.household.id,
            plant_id=plant_id,
            space_id=body.space_id,
            container_id=body.container_id,
            x=body.x,
            y=body.y,
            width=body.width,
            height=body.height,
            actor_user_id=ctx.user.id,
        )
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc
    return {
        "id": str(p.id),
        "plant_id": str(p.plant_id),
        "space_id": str(p.space_id),
        "container_id": str(p.container_id) if p.container_id else None,
        "x": p.x,
        "y": p.y,
    }


@router.delete(
    "/households/{household_id}/plants/{plant_id}/placement",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_placement(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> None:
    await layout_service.remove_placement(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    await db.commit()


@router.delete(
    "/households/{household_id}/sites/{site_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_site(
    site_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("admin"))],
    db: DbSession,
) -> None:
    try:
        await layout_service.delete_site(db, ctx.household.id, site_id)
        await db.commit()
    except LayoutError as exc:
        await db.rollback()
        raise _layout_err(exc) from exc


@router.get("/households/{household_id}/layout/unassigned")
async def unassigned_plants(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> list[dict[str, Any]]:
    placed = select(Placement.plant_id).where(Placement.household_id == ctx.household.id)
    result = await db.execute(
        select(Plant).where(
            Plant.household_id == ctx.household.id,
            Plant.status.in_(["active", "dormant"]),
            Plant.id.not_in(placed),
        )
    )
    return [{"id": str(p.id), "nickname": p.nickname} for p in result.scalars()]


# --- Stats & calendar ---


@router.get("/households/{household_id}/stats/summary")
async def stats_summary(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> dict[str, Any]:
    return await stats_service.summary(db, ctx.household.id)


@router.get("/households/{household_id}/calendar")
async def calendar(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
) -> list[dict[str, Any]]:
    try:
        start = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid date range") from exc
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    return await stats_service.calendar_items(
        db, ctx.household.id, date_from=start, date_to=end
    )


# --- QR labels ---


@router.get("/households/{household_id}/plants/{plant_id}/label.pdf")
async def plant_label_pdf(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> Response:
    result = await db.execute(
        select(Plant)
        .options(selectinload(Plant.taxon))
        .where(Plant.id == plant_id, Plant.household_id == ctx.household.id)
    )
    plant = result.scalar_one_or_none()
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    pdf = build_labels_pdf([plant])
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="label-{plant_id}.pdf"'},
    )


@router.post("/households/{household_id}/labels/pdf")
async def batch_labels_pdf(
    body: LabelsRequest,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> Response:
    result = await db.execute(
        select(Plant)
        .options(selectinload(Plant.taxon))
        .where(
            Plant.household_id == ctx.household.id,
            Plant.id.in_(body.plant_ids),
        )
    )
    plants = list(result.scalars())
    if not plants:
        raise HTTPException(status_code=404, detail="No plants found")
    pdf = build_labels_pdf(plants)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="plant-labels.pdf"'},
    )
