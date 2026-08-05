"""Layout services — sites, garden/room spaces, pots (containers), plant placements."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.layout.models import Container, Placement, Site, Space
from app.modules.plants.models import Plant
from app.modules.timeline import service as timeline_service

# Map scale: pixels per metre when drawing garden borders
PX_PER_METER = 40
MIN_CANVAS = 200
MAX_CANVAS = 4000


class LayoutError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def canvas_from_metres(
    length_m: float | None, width_m: float | None
) -> tuple[int, int]:
    """Convert real-world metres → canvas pixels (length = horizontal)."""
    if length_m and length_m > 0 and width_m and width_m > 0:
        w = int(max(MIN_CANVAS, min(MAX_CANVAS, length_m * PX_PER_METER)))
        h = int(max(MIN_CANVAS, min(MAX_CANVAS, width_m * PX_PER_METER)))
        return w, h
    return 1000, 800


async def list_sites(db: AsyncSession, household_id: uuid.UUID) -> list[Site]:
    result = await db.execute(
        select(Site)
        .options(
            selectinload(Site.spaces).selectinload(Space.containers),
            selectinload(Site.spaces).selectinload(Space.placements),
        )
        .where(Site.household_id == household_id)
        .order_by(Site.sort_order, Site.name)
    )
    return list(result.scalars())


async def create_site(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    name: str,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Site:
    site = Site(
        household_id=household_id,
        name=name.strip(),
        latitude=latitude,
        longitude=longitude,
    )
    db.add(site)
    await db.flush()
    return site


async def create_space(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    site_id: uuid.UUID,
    name: str,
    kind: str = "room",
    canvas_width: int = 1000,
    canvas_height: int = 800,
    length_m: float | None = None,
    width_m: float | None = None,
    notes: str | None = None,
) -> Space:
    site = await db.get(Site, site_id)
    if site is None or site.household_id != household_id:
        raise LayoutError("Site not found", status_code=404)
    if length_m or width_m:
        canvas_width, canvas_height = canvas_from_metres(length_m, width_m)
    space = Space(
        household_id=household_id,
        site_id=site_id,
        name=name.strip(),
        kind=kind,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        length_m=length_m,
        width_m=width_m,
        notes=notes,
    )
    db.add(space)
    await db.flush()
    return space


async def update_space(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    space_id: uuid.UUID,
    name: str | None = None,
    kind: str | None = None,
    length_m: float | None = None,
    width_m: float | None = None,
    notes: str | None = None,
    canvas_width: int | None = None,
    canvas_height: int | None = None,
) -> Space:
    space = await db.get(Space, space_id)
    if space is None or space.household_id != household_id:
        raise LayoutError("Space not found", status_code=404)
    if name is not None:
        space.name = name.strip()
    if kind is not None:
        space.kind = kind
    if notes is not None:
        space.notes = notes
    # Real-world dimensions drive canvas when provided
    if length_m is not None:
        space.length_m = length_m if length_m > 0 else None
    if width_m is not None:
        space.width_m = width_m if width_m > 0 else None
    if space.length_m and space.width_m:
        space.canvas_width, space.canvas_height = canvas_from_metres(
            space.length_m, space.width_m
        )
    else:
        if canvas_width is not None:
            space.canvas_width = max(MIN_CANVAS, min(MAX_CANVAS, canvas_width))
        if canvas_height is not None:
            space.canvas_height = max(MIN_CANVAS, min(MAX_CANVAS, canvas_height))
    await db.flush()
    return space


async def duplicate_container(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    container_id: uuid.UUID,
    offset: float = 40,
) -> Container:
    """Copy a pot (shape/size) to a nearby position — plants are not copied."""
    c = await db.get(Container, container_id)
    if c is None or c.household_id != household_id:
        raise LayoutError("Pot not found", status_code=404)
    path = None
    if c.path_json:
        path = [[float(p[0]) + offset, float(p[1]) + offset] for p in c.path_json]
    return await create_container(
        db,
        household_id=household_id,
        space_id=c.space_id,
        name=f"{c.name} (copy)" if not c.name.endswith("(copy)") else c.name,
        kind=c.kind or "circle",
        x=c.x + offset,
        y=c.y + offset,
        width=c.width or 56,
        height=c.height or 56,
        path_json=path,
        emoji=c.emoji,
    )


async def create_container(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    space_id: uuid.UUID,
    name: str,
    kind: str | None = "circle",
    x: float = 0,
    y: float = 0,
    width: float | None = 56,
    height: float | None = 56,
    path_json: list | None = None,
    emoji: str | None = None,
) -> Container:
    space = await db.get(Space, space_id)
    if space is None or space.household_id != household_id:
        raise LayoutError("Space not found", status_code=404)
    path = list(path_json or [])
    # Derive bounding box from freehand path when provided
    if path and len(path) >= 2:
        xs = [float(p[0]) for p in path]
        ys = [float(p[1]) for p in path]
        x = min(xs)
        y = min(ys)
        width = max(xs) - x or 40
        height = max(ys) - y or 40
        kind = kind or "polygon"
    em = (emoji or "").strip()[:8] or None
    container = Container(
        household_id=household_id,
        space_id=space_id,
        name=name.strip() or "Pot",
        kind=kind or "circle",
        emoji=em,
        x=x,
        y=y,
        width=width,
        height=height,
        path_json=path,
    )
    db.add(container)
    await db.flush()
    return container


async def update_container(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    container_id: uuid.UUID,
    name: str | None = None,
    kind: str | None = None,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    height: float | None = None,
    path_json: list | None = None,
    emoji: str | None = None,
) -> Container:
    c = await db.get(Container, container_id)
    if c is None or c.household_id != household_id:
        raise LayoutError("Pot not found", status_code=404)
    if name is not None:
        c.name = name.strip()
    if kind is not None:
        c.kind = kind
    if emoji is not None:
        c.emoji = emoji.strip()[:8] or None
    if path_json is not None:
        c.path_json = list(path_json)
        if c.path_json and len(c.path_json) >= 2:
            xs = [float(p[0]) for p in c.path_json]
            ys = [float(p[1]) for p in c.path_json]
            c.x = min(xs)
            c.y = min(ys)
            c.width = max(xs) - c.x or 40
            c.height = max(ys) - c.y or 40
    if x is not None:
        # Move freehand path with the box
        if c.path_json and len(c.path_json) >= 2 and c.x is not None:
            dx = x - c.x
            c.path_json = [[float(p[0]) + dx, float(p[1])] for p in c.path_json]
        c.x = x
    if y is not None:
        if c.path_json and len(c.path_json) >= 2 and c.y is not None:
            dy = y - c.y
            c.path_json = [[float(p[0]), float(p[1]) + dy] for p in c.path_json]
        c.y = y
    if width is not None:
        c.width = width
    if height is not None:
        c.height = height
    await db.flush()
    return c


async def delete_container(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    container_id: uuid.UUID,
) -> None:
    c = await db.get(Container, container_id)
    if c is None or c.household_id != household_id:
        raise LayoutError("Pot not found", status_code=404)
    # Detach plants but keep them on the space at the pot position
    result = await db.execute(
        select(Placement).where(Placement.container_id == container_id)
    )
    for pl in result.scalars():
        pl.container_id = None
        pl.x = c.x
        pl.y = c.y
    await db.delete(c)
    await db.flush()


async def upsert_placement(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    plant_id: uuid.UUID,
    space_id: uuid.UUID,
    container_id: uuid.UUID | None = None,
    x: float = 0,
    y: float = 0,
    width: float | None = 64,
    height: float | None = 64,
    actor_user_id: uuid.UUID | None = None,
) -> Placement:
    plant = await db.get(Plant, plant_id)
    if plant is None or plant.household_id != household_id:
        raise LayoutError("Plant not found", status_code=404)
    space = await db.get(Space, space_id)
    if space is None or space.household_id != household_id:
        raise LayoutError("Space not found", status_code=404)
    if container_id:
        c = await db.get(Container, container_id)
        if c is None or c.household_id != household_id:
            raise LayoutError("Pot not found", status_code=404)
        # Snap plant to pot position when assigned to a pot
        x = c.x
        y = c.y
        if c.width:
            width = c.width
        if c.height:
            height = c.height

    result = await db.execute(select(Placement).where(Placement.plant_id == plant_id))
    placement = result.scalar_one_or_none()
    old_space = placement.space_id if placement else None

    if placement is None:
        placement = Placement(
            household_id=household_id,
            plant_id=plant_id,
            space_id=space_id,
            container_id=container_id,
            x=x,
            y=y,
            width=width,
            height=height,
        )
        db.add(placement)
    else:
        placement.space_id = space_id
        placement.container_id = container_id
        placement.x = x
        placement.y = y
        placement.width = width
        placement.height = height

    await db.flush()

    if old_space != space_id:
        await timeline_service.create_event(
            db,
            household_id=household_id,
            event_type="relocated",
            plant_id=plant_id,
            actor_user_id=actor_user_id,
            payload={
                "from_space_id": str(old_space) if old_space else None,
                "to_space_id": str(space_id),
                "container_id": str(container_id) if container_id else None,
            },
        )
    return placement


async def remove_placement(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    plant_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(Placement).where(
            Placement.plant_id == plant_id,
            Placement.household_id == household_id,
        )
    )
    placement = result.scalar_one_or_none()
    if placement:
        await db.delete(placement)
        await db.flush()


async def placement_path(db: AsyncSession, plant_id: uuid.UUID) -> str | None:
    result = await db.execute(
        select(Placement)
        .options(
            selectinload(Placement.space).selectinload(Space.site),
        )
        .where(Placement.plant_id == plant_id)
    )
    placement = result.scalar_one_or_none()
    if not placement or not placement.space:
        return None
    site_name = placement.space.site.name if placement.space.site else ""
    parts = [p for p in [site_name, placement.space.name] if p]
    return " / ".join(parts) if parts else None


async def delete_site(db: AsyncSession, household_id: uuid.UUID, site_id: uuid.UUID) -> None:
    site = await db.get(Site, site_id)
    if site is None or site.household_id != household_id:
        raise LayoutError("Site not found", status_code=404)
    await db.delete(site)
    await db.flush()


async def delete_space(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    space_id: uuid.UUID,
) -> None:
    """Remove a room/garden area. Pots go with it; plant placements on this space are dropped
    (plants themselves stay in the collection, unassigned from the map)."""
    space = await db.get(Space, space_id)
    if space is None or space.household_id != household_id:
        raise LayoutError("Room/area not found", status_code=404)
    await db.delete(space)
    await db.flush()
