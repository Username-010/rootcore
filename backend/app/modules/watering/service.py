"""Watering state persistence and recompute."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.plants.models import Plant
from app.modules.tasks.models import Task, TaskPlant
from app.modules.taxonomy.models import Taxon
from app.modules.timeline.service import count_waterings
from app.modules.watering.engine import WateringRecommendation, compute_baseline
from app.modules.watering.models import WateringState


async def get_watering_state(db: AsyncSession, plant_id: uuid.UUID) -> WateringState | None:
    result = await db.execute(select(WateringState).where(WateringState.plant_id == plant_id))
    return result.scalar_one_or_none()


async def ensure_watering_state(
    db: AsyncSession,
    *,
    plant: Plant,
) -> WateringState:
    state = await get_watering_state(db, plant.id)
    if state is None:
        state = WateringState(
            plant_id=plant.id,
            household_id=plant.household_id,
            urgency="ok",
            factor_breakdown=[],
            feedback_counts={"too_dry": 0, "ok": 0, "too_wet": 0},
        )
        db.add(state)
        await db.flush()
    return state


async def recompute_plant(
    db: AsyncSession,
    plant: Plant,
    *,
    last_watered_at: datetime | None = None,
    set_last_watered: bool = False,
) -> tuple[WateringState, WateringRecommendation]:
    """Recompute watering state and upsert engine watering task.

    Pass set_last_watered=True to force last_watered_at (including None when undoing).
    """
    # Ensure taxon/care loaded
    if plant.taxon_id and plant.taxon is None:
        result = await db.execute(
            select(Plant)
            .options(selectinload(Plant.taxon).selectinload(Taxon.care_profile))
            .where(Plant.id == plant.id)
        )
        plant = result.scalar_one()

    state = await ensure_watering_state(db, plant=plant)
    if set_last_watered or last_watered_at is not None:
        state.last_watered_at = last_watered_at

    care = plant.taxon.care_profile if plant.taxon else None
    waterings = await count_waterings(db, plant.id)

    weather_temp = weather_humidity = weather_precip = None
    tz_name = "UTC"
    try:
        from app.modules.households.models import Household
        from app.modules.weather import service as weather_service

        household = await db.get(Household, plant.household_id)
        if household is not None:
            tz_name = household.timezone or "UTC"
            snap = await weather_service.get_household_weather(db, household)
            if snap is not None:
                weather_temp = snap.current_temp_c
                weather_humidity = snap.current_humidity
                weather_precip = snap.precip_next_24h_mm
    except Exception:
        pass

    rec = compute_baseline(
        last_watered_at=state.last_watered_at,
        baseline_min_days=care.baseline_interval_days_min if care else None,
        baseline_max_days=care.baseline_interval_days_max if care else None,
        pot_size_liters=plant.pot_size_liters,
        pot_material=plant.pot_material,
        soil_type=plant.soil_type,
        environment=plant.environment,
        growth_stage=plant.growth_stage,
        interval_bias_days=state.interval_bias_days or 0.0,
        waterings_logged=waterings,
        manual_next_due_at=state.manual_next_due_at,
        paused_until=state.paused_until,
        weather_temp_c=weather_temp,
        weather_humidity=weather_humidity,
        weather_precip_24h_mm=weather_precip,
        timezone=tz_name,
    )

    state.next_due_at = rec.next_due_at
    state.urgency = rec.urgency
    state.recommended_amount = rec.recommended_amount
    state.confidence = rec.confidence
    state.moisture_score = rec.moisture_score
    state.factor_breakdown = rec.factor_breakdown
    state.last_computed_at = datetime.now(UTC)
    await db.flush()

    await _upsert_engine_water_task(db, plant=plant, state=state)
    try:
        from app.modules.care.schedule import schedule_care_tasks

        await schedule_care_tasks(db, plant)
    except Exception:
        pass
    return state, rec


async def _upsert_engine_water_task(
    db: AsyncSession,
    *,
    plant: Plant,
    state: WateringState,
) -> None:
    if plant.status not in {"active", "dormant"}:
        return
    source_key = f"engine:water:{plant.id}"
    result = await db.execute(
        select(Task).where(
            Task.household_id == plant.household_id,
            Task.source_key == source_key,
        )
    )
    task = result.scalar_one_or_none()
    title = f"Water {plant.nickname}"
    if task is None:
        task = Task(
            household_id=plant.household_id,
            title=title,
            type="water",
            status="open",
            priority="normal" if state.urgency in {"ok", "soon"} else "high",
            due_at=state.next_due_at,
            source="engine",
            source_key=source_key,
            create_event_on_complete=True,
            event_type_on_complete="watered",
            payload={
                "plant_id": str(plant.id),
                "recommended_amount": state.recommended_amount,
                "urgency": state.urgency,
            },
        )
        db.add(task)
        await db.flush()
        db.add(TaskPlant(task_id=task.id, plant_id=plant.id))
    else:
        if task.status == "done" and state.urgency in {"due", "overdue", "soon"}:
            task.status = "open"
            task.completed_at = None
            task.completed_by_user_id = None
        task.title = title
        task.due_at = state.next_due_at
        task.priority = "high" if state.urgency in {"due", "overdue"} else "normal"
        task.payload = {
            **(task.payload or {}),
            "recommended_amount": state.recommended_amount,
            "urgency": state.urgency,
        }
    await db.flush()


async def list_due(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    limit: int = 50,
) -> list[tuple[Plant, WateringState]]:
    result = await db.execute(
        select(Plant, WateringState)
        .join(WateringState, WateringState.plant_id == Plant.id)
        .where(
            Plant.household_id == household_id,
            Plant.status.in_(["active", "dormant"]),
            WateringState.urgency.in_(["soon", "due", "overdue"]),
        )
        .order_by(WateringState.next_due_at.asc().nulls_last())
        .limit(min(limit, 100))
    )
    return list(result.all())


async def apply_feedback(
    db: AsyncSession,
    state: WateringState,
    rating: str,
) -> WateringState:
    """EMA-style interval bias update from user moisture feedback."""
    counts = dict(state.feedback_counts or {"too_dry": 0, "ok": 0, "too_wet": 0})
    if rating not in counts:
        rating = "ok"
    counts[rating] = int(counts.get(rating, 0)) + 1
    state.feedback_counts = counts

    # Adjust bias: too dry → water sooner (negative days), too wet → later
    delta = {"too_dry": -0.5, "ok": 0.0, "too_wet": 0.5}.get(rating, 0.0)
    # EMA
    state.interval_bias_days = round(
        0.7 * (state.interval_bias_days or 0.0) + 0.3 * (
            (state.interval_bias_days or 0.0) + delta
        ),
        3,
    )
    # Clamp learning
    state.interval_bias_days = max(-7.0, min(7.0, state.interval_bias_days))
    await db.flush()
    return state
