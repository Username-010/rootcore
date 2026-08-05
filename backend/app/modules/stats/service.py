"""Stats aggregations and care calendar projections."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.plants.models import Plant
from app.modules.tasks.models import Task
from app.modules.taxonomy.models import Taxon
from app.modules.timeline.models import Event


async def summary(db: AsyncSession, household_id: uuid.UUID) -> dict[str, Any]:
    plants = await db.execute(
        select(Plant.status, func.count())
        .where(Plant.household_id == household_id)
        .group_by(Plant.status)
    )
    by_status = {row[0]: int(row[1]) for row in plants.all()}
    active = by_status.get("active", 0) + by_status.get("dormant", 0)
    deceased = by_status.get("deceased", 0)
    total_for_survival = active + deceased
    survival = (
        (1.0 - deceased / total_for_survival) if total_for_survival else None
    )

    value = await db.execute(
        select(func.coalesce(func.sum(Plant.estimated_value), 0)).where(
            Plant.household_id == household_id,
            Plant.status.in_(["active", "dormant"]),
        )
    )

    since = datetime.now(UTC) - timedelta(days=30)
    waterings = await db.execute(
        select(func.count())
        .select_from(Event)
        .where(
            Event.household_id == household_id,
            Event.type == "watered",
            Event.deleted_at.is_(None),
            Event.occurred_at >= since,
        )
    )
    tasks_done = await db.execute(
        select(func.count())
        .select_from(Task)
        .where(
            Task.household_id == household_id,
            Task.status == "done",
            Task.completed_at >= since,
        )
    )
    tasks_open = await db.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.household_id == household_id, Task.status == "open")
    )

    # Rough water volume estimate: assume 250ml per watering if not recorded
    events = await db.execute(
        select(Event.payload)
        .where(
            Event.household_id == household_id,
            Event.type == "watered",
            Event.deleted_at.is_(None),
            Event.occurred_at >= since,
        )
    )
    volume = 0.0
    for (payload,) in events.all():
        if payload and payload.get("volume_ml"):
            volume += float(payload["volume_ml"])
        else:
            volume += 250.0

    return {
        "plants_by_status": by_status,
        "plants_active": active,
        "plants_deceased": deceased,
        "survival_rate": round(survival, 4) if survival is not None else None,
        "collection_value": float(value.scalar_one() or 0),
        "waterings_30d": int(waterings.scalar_one()),
        "estimated_water_ml_30d": round(volume, 1),
        "tasks_completed_30d": int(tasks_done.scalar_one()),
        "tasks_open": int(tasks_open.scalar_one()),
    }


def _interval_days(plant: Plant, state_interval: float | None = None) -> float:
    if state_interval and state_interval > 0:
        return state_interval
    care = plant.taxon.care_profile if plant.taxon else None
    if care and care.baseline_interval_days_min is not None:
        lo = float(care.baseline_interval_days_min)
        hi = float(care.baseline_interval_days_max or lo)
        return max(2.0, (lo + hi) / 2.0)
    return 7.0


def _project_due_dates(
    next_due: datetime,
    interval_days: float,
    date_from: datetime,
    date_to: datetime,
    *,
    max_occurrences: int = 12,
) -> list[datetime]:
    """Walk watering due dates into the requested window (inclusive)."""
    if interval_days < 1:
        interval_days = 7.0
    cursor = next_due
    if cursor.tzinfo is None:
        cursor = cursor.replace(tzinfo=UTC)
    # Advance until we reach the window (or slightly past start)
    guard = 0
    while cursor < date_from and guard < 200:
        cursor = cursor + timedelta(days=interval_days)
        guard += 1
    out: list[datetime] = []
    while cursor <= date_to and len(out) < max_occurrences:
        if cursor >= date_from:
            out.append(cursor)
        cursor = cursor + timedelta(days=interval_days)
    return out


async def calendar_items(
    db: AsyncSession,
    household_id: uuid.UUID,
    *,
    date_from: datetime,
    date_to: datetime,
) -> list[dict[str, Any]]:
    from app.modules.layout.models import Placement, Site, Space
    from app.modules.watering.models import WateringState

    # Active plant ids — skip tasks for archived/deceased plants
    active_plant_ids = set(
        (
            await db.execute(
                select(Plant.id).where(
                    Plant.household_id == household_id,
                    Plant.status.in_(["active", "dormant"]),
                )
            )
        )
        .scalars()
        .all()
    )

    # Tasks (fertilize / prune / repot / custom) with plant ids
    tasks = await db.execute(
        select(Task)
        .options(selectinload(Task.plant_links))
        .where(
            Task.household_id == household_id,
            Task.due_at.is_not(None),
            Task.due_at >= date_from,
            Task.due_at <= date_to,
            Task.status != "cancelled",
        )
    )
    items: list[dict[str, Any]] = []
    for t in tasks.scalars():
        plant_ids = [tp.plant_id for tp in (t.plant_links or [])]
        payload_pid = (t.payload or {}).get("plant_id")
        # Skip engine tasks whose plant is archived/gone
        if plant_ids:
            if not any(pid in active_plant_ids for pid in plant_ids):
                continue
            plant_id = plant_ids[0]
        elif payload_pid:
            try:
                import uuid as _uuid

                pid = _uuid.UUID(str(payload_pid))
            except Exception:
                pid = None
            if pid is not None and pid not in active_plant_ids:
                continue
            plant_id = pid
        else:
            plant_id = None
        items.append(
            {
                "id": str(t.id),
                "kind": "task",
                "title": t.title,
                "type": t.type,
                "status": t.status,
                "at": t.due_at.isoformat() if t.due_at else None,
                "plant_id": str(plant_id) if plant_id else None,
                "room": None,
                "source": t.source,
                "description": t.description,
            }
        )

    events = await db.execute(
        select(Event).where(
            Event.household_id == household_id,
            Event.deleted_at.is_(None),
            Event.occurred_at >= date_from,
            Event.occurred_at <= date_to,
        )
    )
    for e in events.scalars():
        items.append(
            {
                "id": str(e.id),
                "kind": "event",
                "title": e.type,
                "type": e.type,
                "status": None,
                "at": e.occurred_at.isoformat(),
                "plant_id": str(e.plant_id) if e.plant_id else None,
                "room": None,
            }
        )

    # Planned watering: project recurring due dates across the month window
    watering_rows = await db.execute(
        select(Plant, WateringState, Placement, Space, Site)
        .options(selectinload(Plant.taxon).selectinload(Taxon.care_profile))
        .join(WateringState, WateringState.plant_id == Plant.id)
        .outerjoin(Placement, Placement.plant_id == Plant.id)
        .outerjoin(Space, Space.id == Placement.space_id)
        .outerjoin(Site, Site.id == Space.site_id)
        .where(
            Plant.household_id == household_id,
            Plant.status.in_(["active", "dormant"]),
            WateringState.next_due_at.is_not(None),
        )
    )
    for plant, state, _placement, space, site in watering_rows.all():
        room = None
        if space is not None:
            site_name = site.name if site is not None else ""
            room = " / ".join([p for p in [site_name, space.name] if p]) or space.name
        interval = _interval_days(plant)
        assert state.next_due_at is not None
        for i, due in enumerate(
            _project_due_dates(state.next_due_at, interval, date_from, date_to)
        ):
            # First occurrence uses live urgency; later projections are planned
            urgency = state.urgency if i == 0 and due == state.next_due_at else "planned"
            items.append(
                {
                    "id": f"water-{plant.id}-{due.date().isoformat()}",
                    "kind": "watering",
                    "title": f"Water {plant.nickname}",
                    "type": "water",
                    "status": urgency,
                    "at": due.isoformat(),
                    "plant_id": str(plant.id),
                    "room": room or "Unassigned",
                    "recommended_amount": state.recommended_amount,
                }
            )

    items.sort(key=lambda x: x.get("at") or "")
    return items


async def care_brief(
    db: AsyncSession,
    household_id: uuid.UUID,
) -> dict[str, Any]:
    """Quick dashboard summary: water due (same rules as water plan), upcoming, care tasks."""
    from app.modules.layout.models import Placement, Site, Space
    from app.modules.watering.models import WateringState

    now = datetime.now(UTC)
    end_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    in_3d = now + timedelta(days=3)
    in_7d = now + timedelta(days=7)

    # Match water plan: urgency soon / due / overdue (not only next_due ≤ midnight)
    water_rows = await db.execute(
        select(Plant, WateringState, Placement, Space, Site)
        .options(selectinload(Plant.taxon))
        .join(WateringState, WateringState.plant_id == Plant.id)
        .outerjoin(Placement, Placement.plant_id == Plant.id)
        .outerjoin(Space, Space.id == Placement.space_id)
        .outerjoin(Site, Site.id == Space.site_id)
        .where(
            Plant.household_id == household_id,
            Plant.status.in_(["active", "dormant"]),
            WateringState.urgency.in_(["soon", "due", "overdue"]),
        )
        .order_by(WateringState.next_due_at.asc().nulls_last())
    )
    water_today: list[dict[str, Any]] = []
    by_zone: dict[str, list[str]] = {}
    for plant, state, _pl, space, site in water_rows.all():
        zone = "Unassigned"
        if space is not None:
            site_name = site.name if site else ""
            zone = " / ".join([p for p in [site_name, space.name] if p]) or space.name
        attrs = plant.custom_attributes or {}
        emoji = attrs.get("emoji") if isinstance(attrs.get("emoji"), str) else None
        water_today.append(
            {
                "plant_id": str(plant.id),
                "nickname": plant.nickname,
                "emoji": (emoji or "🪴")[:8],
                "urgency": state.urgency,
                "room": zone,
                "next_due_at": state.next_due_at.isoformat() if state.next_due_at else None,
                "recommended_amount": state.recommended_amount,
                "amount_label": {
                    "light": "Light water",
                    "deep": "Deep soak",
                    "normal": "Normal water",
                }.get(state.recommended_amount or "normal", "Normal water"),
            }
        )
        by_zone.setdefault(zone, []).append(plant.nickname)

    # Upcoming watering (1–3 days)
    upcoming_water = await db.execute(
        select(Plant, WateringState, Placement, Space, Site)
        .join(WateringState, WateringState.plant_id == Plant.id)
        .outerjoin(Placement, Placement.plant_id == Plant.id)
        .outerjoin(Space, Space.id == Placement.space_id)
        .outerjoin(Site, Site.id == Space.site_id)
        .where(
            Plant.household_id == household_id,
            Plant.status.in_(["active", "dormant"]),
            WateringState.next_due_at.is_not(None),
            WateringState.next_due_at > end_today,
            WateringState.next_due_at <= in_3d,
        )
    )
    upcoming: list[dict[str, Any]] = []
    for plant, state, _pl, space, site in upcoming_water.all():
        zone = "Unassigned"
        if space is not None:
            site_name = site.name if site else ""
            zone = " / ".join([p for p in [site_name, space.name] if p]) or space.name
        upcoming.append(
            {
                "plant_id": str(plant.id),
                "nickname": plant.nickname,
                "kind": "water",
                "room": zone,
                "at": state.next_due_at.isoformat() if state.next_due_at else None,
            }
        )

    # Engine tasks in next 7 days grouped by type
    tasks = await db.execute(
        select(Task)
        .options(selectinload(Task.plant_links))
        .where(
            Task.household_id == household_id,
            Task.status == "open",
            Task.due_at.is_not(None),
            Task.due_at <= in_7d,
            Task.type.in_(["prune", "fertilize", "repot", "water"]),
        )
        .order_by(Task.due_at)
    )
    prune: list[dict[str, Any]] = []
    fertilize: list[dict[str, Any]] = []
    repot: list[dict[str, Any]] = []
    for t in tasks.scalars():
        entry = {
            "task_id": str(t.id),
            "title": t.title,
            "type": t.type,
            "at": t.due_at.isoformat() if t.due_at else None,
            "plant_id": str(t.plant_links[0].plant_id) if t.plant_links else None,
        }
        if t.type == "prune":
            prune.append(entry)
        elif t.type == "fertilize":
            fertilize.append(entry)
        elif t.type == "repot":
            repot.append(entry)

    lines: list[str] = []
    if water_today:
        names = ", ".join(p["nickname"] for p in water_today[:6])
        more = f" +{len(water_today) - 6}" if len(water_today) > 6 else ""
        zones = ", ".join(f"{z} ({len(v)})" for z, v in list(by_zone.items())[:4])
        lines.append(
            f"💧 Water now ({len(water_today)}): {names}{more}"
            + (f" · zones: {zones}" if zones else "")
        )
    else:
        lines.append("💧 No watering due right now")
    if upcoming:
        names = ", ".join(p["nickname"] for p in upcoming[:5])
        lines.append(f"⏱ Upcoming in 3 days — water {names}")
    if prune:
        lines.append("✂ Prune: " + ", ".join(p["title"].replace("Prune ", "") for p in prune[:5]))
    if fertilize:
        names = ", ".join(p["title"].replace("Fertilize ", "") for p in fertilize[:5])
        lines.append("🌿 Fertilize: " + names)
    if repot:
        lines.append("🪴 Repot: " + ", ".join(p["title"].replace("Repot ", "") for p in repot[:5]))

    return {
        "lines": lines,
        "water_today": water_today,
        "water_by_zone": {k: v for k, v in by_zone.items()},
        "upcoming": upcoming,
        "prune": prune,
        "fertilize": fertilize,
        "repot": repot,
    }
