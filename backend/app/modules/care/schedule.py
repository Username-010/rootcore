"""Generate fertilize / prune / repot engine tasks from plant + care profile."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.plants.models import Plant
from app.modules.tasks.models import Task, TaskPlant
from app.modules.timeline.models import Event

# Cluster windows used across the garden so calendar looks coherent
SPRING_PRUNE = (3, 15)  # mid-March cutback
AUTUMN_PRUNE = (11, 1)  # early November tidy


async def _last_event_date(
    db: AsyncSession, plant_id: uuid.UUID, event_type: str
) -> date | None:
    result = await db.execute(
        select(Event.occurred_at)
        .where(
            Event.plant_id == plant_id,
            Event.type == event_type,
            Event.deleted_at.is_(None),
        )
        .order_by(Event.occurred_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return row.date() if hasattr(row, "date") else row


async def _upsert_task(
    db: AsyncSession,
    *,
    plant: Plant,
    task_type: str,
    title: str,
    due: datetime,
    event_type: str,
    description: str | None = None,
    payload: dict | None = None,
) -> None:
    source_key = f"engine:{task_type}:{plant.id}"
    result = await db.execute(
        select(Task).where(
            Task.household_id == plant.household_id,
            Task.source_key == source_key,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        task = Task(
            household_id=plant.household_id,
            title=title,
            description=description,
            type=task_type,
            status="open",
            priority="normal",
            due_at=due,
            source="engine",
            source_key=source_key,
            create_event_on_complete=True,
            event_type_on_complete=event_type,
            payload=payload or {"plant_id": str(plant.id)},
        )
        db.add(task)
        await db.flush()
        db.add(TaskPlant(task_id=task.id, plant_id=plant.id))
    else:
        if task.status == "done" and due <= datetime.now(UTC) + timedelta(days=3):
            if task.completed_at and (datetime.now(UTC) - task.completed_at).days > 7:
                task.status = "open"
                task.completed_at = None
                task.completed_by_user_id = None
        if task.status == "open":
            task.due_at = due
            task.title = title
            if description is not None:
                task.description = description
            task.payload = {**(task.payload or {}), **(payload or {})}
    await db.flush()


def _fertilize_interval_days(plant: Plant) -> int:
    care = plant.taxon.care_profile if plant.taxon else None
    extra = (care.extra if care else None) or {}
    if "fertilize_interval_days" in extra:
        return int(extra["fertilize_interval_days"])
    env = (plant.environment or "indoor").lower()
    moisture = (care.moisture_preference if care else None) or "medium"
    if env == "outdoor":
        return 28 if moisture != "dry" else 42
    if moisture == "dry":
        return 56
    return 35


def _next_fixed(now: date, month: int, day: int) -> date:
    candidate = date(now.year, month, day)
    if candidate < now - timedelta(days=21):
        candidate = date(now.year + 1, month, day)
    return candidate


def _prune_plan(plant: Plant, now: date) -> tuple[date, str, str, list[int]] | None:
    """Return (due, season_label, reason, prune_months) or None if no prune."""
    care = plant.taxon.care_profile if plant.taxon else None
    extra = (care.extra if care else None) or {}
    env = (plant.environment or "indoor").lower()
    outdoor = env in {"outdoor", "greenhouse"}

    prune_months: list[int] = []
    raw = extra.get("prune_months")
    if isinstance(raw, list) and raw:
        prune_months = [int(m) for m in raw if 1 <= int(m) <= 12]
    bloom = [int(m) for m in (extra.get("bloom_months") or []) if 1 <= int(m) <= 12]

    if not prune_months:
        if not outdoor:
            # Indoor foliage — no forced prune unless profile says so
            return None
        if bloom:
            last = max(bloom)
            if last <= 5:
                prune_months = [last + 1 if last < 12 else 12]
            elif last <= 9:
                # Summer garden plants: spring cutback + optional autumn tidy
                prune_months = [3, 11]
            else:
                prune_months = [3]
        else:
            prune_months = [3]

    # Pick next due among windows; prefer March / November clustering
    candidates: list[tuple[date, str]] = []
    for m in sorted(set(prune_months)):
        if m == 3:
            candidates.append((_next_fixed(now, *SPRING_PRUNE), "spring cutback"))
        elif m == 11:
            candidates.append((_next_fixed(now, *AUTUMN_PRUNE), "autumn tidy"))
        else:
            candidates.append((_next_fixed(now, m, 15), f"month {m} prune"))

    candidates.sort(key=lambda c: c[0])
    due, season = candidates[0]

    # Build human reason
    bloom_txt = ""
    if bloom:
        names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        bloom_txt = (
            " Typical bloom: "
            + ", ".join(names[m - 1] for m in sorted(set(bloom)))
            + "."
        )

    alt = ""
    if len(candidates) > 1:
        alt_bits = [f"{s} ({d.strftime('%b')})" for d, s in candidates[1:]]
        alt = " Also good: " + ", ".join(alt_bits) + "."

    if season == "spring cutback":
        reason = (
            "Spring cutback (mid-March) — remove dead stems before new growth."
            + bloom_txt
            + alt
        )
    elif season == "autumn tidy":
        reason = (
            "Autumn tidy (early November) — cut back spent stems before winter."
            + bloom_txt
            + alt
        )
    else:
        reason = f"Suggested prune window: {season}." + bloom_txt + alt

    return due, season, reason, prune_months


def _repot_due(plant: Plant, last_repot: date | None, now: date) -> date | None:
    care = plant.taxon.care_profile if plant.taxon else None
    extra = (care.extra if care else None) or {}
    # Outdoor garden beds rarely need pot repot
    if (plant.environment or "").lower() == "outdoor" and not plant.pot_size_liters:
        months = int(extra.get("repot_every_months") or 0)
        if months <= 0:
            return None
    months = int(extra.get("repot_every_months") or 24)
    base = last_repot or plant.acquired_at or now
    year = base.year + (base.month + months - 1) // 12
    month = (base.month + months - 1) % 12 + 1
    day = min(base.day, 28)
    due = date(year, month, day)
    if due < now - timedelta(days=60):
        return now + timedelta(days=14)
    return due


async def schedule_care_tasks(db: AsyncSession, plant: Plant) -> None:
    if plant.status not in {"active", "dormant"}:
        return

    now = datetime.now(UTC)
    today = now.date()

    # Fertilize
    last_fert = await _last_event_date(db, plant.id, "fertilized")
    interval = _fertilize_interval_days(plant)
    month = today.month
    if plant.environment in {"outdoor", "greenhouse"} and month in (11, 12, 1, 2):
        fert_due = date(today.year if month < 11 else today.year + 1, 3, 15)
        fert_note = "Resume feeding in spring (outdoor winter pause)."
    else:
        start = last_fert or plant.acquired_at or today
        fert_due = start + timedelta(days=interval)
        if fert_due < today:
            fert_due = today + timedelta(days=3)
        fert_note = f"About every {interval} days in the growing season."
    await _upsert_task(
        db,
        plant=plant,
        task_type="fertilize",
        title=f"Fertilize {plant.nickname}",
        description=fert_note,
        due=datetime.combine(fert_due, datetime.min.time()).replace(tzinfo=UTC),
        event_type="fertilized",
        payload={"plant_id": str(plant.id), "interval_days": interval},
    )

    # Prune
    plan = _prune_plan(plant, today)
    if plan is not None:
        prune_day, season, reason, prune_months = plan
        last_prune = await _last_event_date(db, plant.id, "pruned")
        if last_prune and (prune_day - last_prune).days < 45:
            # Already pruned this window — push to next year same month
            prune_day = date(prune_day.year + 1, prune_day.month, prune_day.day)
        await _upsert_task(
            db,
            plant=plant,
            task_type="prune",
            title=f"Prune {plant.nickname} · {season}",
            description=reason,
            due=datetime.combine(prune_day, datetime.min.time()).replace(tzinfo=UTC),
            event_type="pruned",
            payload={
                "plant_id": str(plant.id),
                "season": season,
                "reason": reason,
                "prune_months": prune_months,
            },
        )

    # Repot
    last_repot = await _last_event_date(db, plant.id, "repotted")
    repot_day = _repot_due(plant, last_repot, today)
    if repot_day is not None:
        await _upsert_task(
            db,
            plant=plant,
            task_type="repot",
            title=f"Repot {plant.nickname}",
            description="Move up a pot size or refresh soil when root-bound.",
            due=datetime.combine(repot_day, datetime.min.time()).replace(tzinfo=UTC),
            event_type="repotted",
            payload={"plant_id": str(plant.id)},
        )
