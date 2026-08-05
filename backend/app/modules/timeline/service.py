"""Timeline event services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.plants.models import Plant
from app.modules.timeline.models import Event


async def create_event(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    event_type: str,
    plant_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    occurred_at: datetime | None = None,
    payload: dict[str, Any] | None = None,
    task_id: uuid.UUID | None = None,
) -> Event:
    occurred = occurred_at or datetime.now(UTC)
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=UTC)
    event = Event(
        household_id=household_id,
        plant_id=plant_id,
        actor_user_id=actor_user_id,
        type=event_type,
        occurred_at=occurred,
        payload=payload or {},
        task_id=task_id,
    )
    db.add(event)
    await db.flush()
    return event


async def list_events(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    plant_id: uuid.UUID | None = None,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Event]:
    stmt = select(Event).where(
        Event.household_id == household_id,
        Event.deleted_at.is_(None),
    )
    if plant_id is not None:
        stmt = stmt.where(Event.plant_id == plant_id)
    if event_type:
        stmt = stmt.where(Event.type == event_type)
    stmt = (
        stmt.order_by(Event.occurred_at.desc(), Event.created_at.desc())
        .limit(min(limit, 100))
        .offset(max(offset, 0))
    )
    result = await db.execute(stmt)
    return list(result.scalars())


async def get_event(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    event_id: uuid.UUID,
) -> Event | None:
    result = await db.execute(
        select(Event).where(
            Event.id == event_id,
            Event.household_id == household_id,
            Event.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def update_event(
    db: AsyncSession,
    event: Event,
    *,
    event_type: str | None = None,
    plant_id: uuid.UUID | None = None,
    clear_plant: bool = False,
    occurred_at: datetime | None = None,
    payload: dict[str, Any] | None = None,
    notes: str | None = None,
) -> Event:
    if event_type is not None:
        event.type = event_type.strip()
    if clear_plant:
        event.plant_id = None
    elif plant_id is not None:
        event.plant_id = plant_id
    if occurred_at is not None:
        occurred = occurred_at
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=UTC)
        event.occurred_at = occurred
    if payload is not None:
        event.payload = dict(payload)
    if notes is not None:
        pl = dict(event.payload or {})
        if notes.strip():
            pl["notes"] = notes.strip()
        else:
            pl.pop("notes", None)
        event.payload = pl
    await db.flush()
    return event


async def soft_delete_event(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    event_id: uuid.UUID,
) -> Event | None:
    event = await get_event(db, household_id=household_id, event_id=event_id)
    if event is None:
        return None
    event.deleted_at = datetime.now(UTC)
    await db.flush()
    return event


async def count_waterings(db: AsyncSession, plant_id: uuid.UUID) -> int:
    from sqlalchemy import func

    result = await db.execute(
        select(func.count())
        .select_from(Event)
        .where(
            Event.plant_id == plant_id,
            Event.type == "watered",
            Event.deleted_at.is_(None),
        )
    )
    return int(result.scalar_one())


async def load_event_context(
    db: AsyncSession, events: list[Event]
) -> dict[uuid.UUID, dict[str, Any]]:
    """Return plant nicknames and actor names for event list decoration."""
    plant_ids = {e.plant_id for e in events if e.plant_id}
    actor_ids = {e.actor_user_id for e in events if e.actor_user_id}
    plants: dict[uuid.UUID, str] = {}
    actors: dict[uuid.UUID, str] = {}
    if plant_ids:
        result = await db.execute(select(Plant.id, Plant.nickname).where(Plant.id.in_(plant_ids)))
        plants = {row[0]: row[1] for row in result.all()}
    if actor_ids:
        result = await db.execute(
            select(User.id, User.display_name).where(User.id.in_(actor_ids))
        )
        actors = {row[0]: row[1] for row in result.all()}
    return {"plants": plants, "actors": actors}
