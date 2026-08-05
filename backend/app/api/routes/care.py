"""Timeline, watering, tasks, and dashboard routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, HouseholdContext, require_household_role
from app.modules.plants.models import Plant
from app.modules.tasks import service as task_service
from app.modules.tasks.schemas import TaskComplete, TaskCreate, TaskPublic, TaskUpdate
from app.modules.tasks.service import TaskError
from app.modules.taxonomy.models import Taxon
from app.modules.timeline import service as timeline_service
from app.modules.timeline.schemas import (
    EventCreate,
    EventPublic,
    EventUpdate,
    FeedbackRequest,
    WateringPublic,
    WaterRequest,
    WaterResponse,
)
from app.modules.watering import service as watering_service

router = APIRouter(prefix="/api/v1", tags=["care"])


def _task_err(exc: TaskError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _task_public(task) -> TaskPublic:
    return TaskPublic(
        id=task.id,
        household_id=task.household_id,
        title=task.title,
        description=task.description,
        type=task.type,
        status=task.status,
        priority=task.priority,
        due_at=task.due_at,
        completed_at=task.completed_at,
        completed_by_user_id=task.completed_by_user_id,
        assignee_user_id=task.assignee_user_id,
        source=task.source,
        plant_ids=[link.plant_id for link in task.plant_links],
        payload=task.payload or {},
        created_at=task.created_at,
    )


async def _event_public(db, event) -> EventPublic:
    ctx = await timeline_service.load_event_context(db, [event])
    return EventPublic(
        id=event.id,
        household_id=event.household_id,
        plant_id=event.plant_id,
        plant_nickname=ctx["plants"].get(event.plant_id) if event.plant_id else None,
        actor_user_id=event.actor_user_id,
        actor_name=ctx["actors"].get(event.actor_user_id) if event.actor_user_id else None,
        type=event.type,
        occurred_at=event.occurred_at,
        payload=event.payload or {},
        task_id=event.task_id,
        created_at=event.created_at,
    )


def _watering_public(plant_id: uuid.UUID, state, rec=None) -> WateringPublic:
    return WateringPublic(
        plant_id=plant_id,
        next_due_at=state.next_due_at,
        urgency=state.urgency,
        recommended_amount=state.recommended_amount,
        confidence=state.confidence,
        moisture_score=state.moisture_score,
        last_watered_at=state.last_watered_at,
        paused_until=state.paused_until,
        manual_next_due_at=state.manual_next_due_at,
        factors=list(state.factor_breakdown or []),
        explanation=rec.explanation if rec else None,
        amount_label=getattr(rec, "amount_label", None) if rec else None,
        amount_howto=getattr(rec, "amount_howto", None) if rec else None,
        amount_ml=getattr(rec, "amount_ml", None) if rec else None,
        volume_guide=getattr(rec, "volume_guide", None) if rec else None,
        best_time_of_day=getattr(rec, "best_time_of_day", None) if rec else None,
        best_time_label=getattr(rec, "best_time_label", None) if rec else None,
        best_time_local=getattr(rec, "best_time_local", None) if rec else None,
        schedule_plain=getattr(rec, "schedule_plain", None) if rec else None,
        weather_note=getattr(rec, "weather_note", None) if rec else None,
        interval_days=getattr(rec, "interval_days", None) if rec else None,
        advice=getattr(rec, "advice", None) if rec else None,
    )


# --- Events / timeline ---


@router.get("/households/{household_id}/events", response_model=list[EventPublic])
async def list_household_events(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
    type: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[EventPublic]:
    events = await timeline_service.list_events(
        db,
        household_id=ctx.household.id,
        event_type=type,
        limit=limit,
        offset=offset,
    )
    context = await timeline_service.load_event_context(db, events)
    return [
        EventPublic(
            id=e.id,
            household_id=e.household_id,
            plant_id=e.plant_id,
            plant_nickname=context["plants"].get(e.plant_id) if e.plant_id else None,
            actor_user_id=e.actor_user_id,
            actor_name=context["actors"].get(e.actor_user_id) if e.actor_user_id else None,
            type=e.type,
            occurred_at=e.occurred_at,
            payload=e.payload or {},
            task_id=e.task_id,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.get(
    "/households/{household_id}/plants/{plant_id}/events",
    response_model=list[EventPublic],
)
async def list_plant_events(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
) -> list[EventPublic]:
    plant = await db.get(Plant, plant_id)
    if plant is None or plant.household_id != ctx.household.id:
        raise HTTPException(status_code=404, detail="Plant not found")
    events = await timeline_service.list_events(
        db, household_id=ctx.household.id, plant_id=plant_id, limit=limit
    )
    return [await _event_public(db, e) for e in events]


@router.post(
    "/households/{household_id}/events",
    response_model=EventPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    body: EventCreate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> EventPublic:
    if body.plant_id:
        plant = await db.get(Plant, body.plant_id)
        if plant is None or plant.household_id != ctx.household.id:
            raise HTTPException(status_code=404, detail="Plant not found")
    event = await timeline_service.create_event(
        db,
        household_id=ctx.household.id,
        event_type=body.type,
        plant_id=body.plant_id,
        actor_user_id=ctx.user.id,
        occurred_at=body.occurred_at,
        payload=body.payload,
    )
    await db.commit()
    await db.refresh(event)
    return await _event_public(db, event)


@router.patch(
    "/households/{household_id}/events/{event_id}",
    response_model=EventPublic,
)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> EventPublic:
    event = await timeline_service.get_event(
        db, household_id=ctx.household.id, event_id=event_id
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if body.plant_id and not body.clear_plant:
        plant = await db.get(Plant, body.plant_id)
        if plant is None or plant.household_id != ctx.household.id:
            raise HTTPException(status_code=404, detail="Plant not found")
    event = await timeline_service.update_event(
        db,
        event,
        event_type=body.type,
        plant_id=body.plant_id,
        clear_plant=body.clear_plant,
        occurred_at=body.occurred_at,
        payload=body.payload,
        notes=body.notes,
    )
    # Watering events: recompute when date/type changes
    if event.plant_id and (body.occurred_at is not None or body.type is not None):
        plant = await db.get(Plant, event.plant_id)
        if plant is not None:
            try:
                await watering_service.recompute_plant(db, plant)
            except Exception:
                pass
    await db.commit()
    return await _event_public(db, event)


@router.delete(
    "/households/{household_id}/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_event(
    event_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> None:
    """Undo a care log: remove event, reopen linked task, restore watering schedule."""
    event = await timeline_service.get_event(
        db, household_id=ctx.household.id, event_id=event_id
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    plant_id = event.plant_id
    event_type = event.type
    task_id = event.task_id

    await timeline_service.soft_delete_event(
        db, household_id=ctx.household.id, event_id=event_id
    )

    # Reopen the task this event completed (if any)
    if task_id:
        task = await task_service.get_task(
            db, household_id=ctx.household.id, task_id=task_id
        )
        if task is not None and task.status == "done":
            await task_service.reopen_task(db, task)

    # Watering: roll last_watered back to previous water event
    if plant_id and event_type == "watered":
        result = await db.execute(
            select(Plant)
            .options(selectinload(Plant.taxon).selectinload(Taxon.care_profile))
            .where(Plant.id == plant_id, Plant.household_id == ctx.household.id)
        )
        plant = result.scalar_one_or_none()
        if plant is not None:
            prev = await timeline_service.list_events(
                db,
                household_id=ctx.household.id,
                plant_id=plant_id,
                event_type="watered",
                limit=1,
            )
            prev_at = prev[0].occurred_at if prev else None
            # No earlier water → treat as overdue so plant returns to the water plan
            if prev_at is None:
                prev_at = datetime.now(UTC) - timedelta(days=21)
            state = await watering_service.ensure_watering_state(db, plant=plant)
            state.last_watered_at = prev_at
            state.manual_next_due_at = None
            await db.flush()
            # Engine water task may have been marked done — reopen
            from app.modules.tasks.models import Task

            source_key = f"engine:water:{plant.id}"
            tres = await db.execute(
                select(Task).where(
                    Task.household_id == ctx.household.id,
                    Task.source_key == source_key,
                    Task.status == "done",
                )
            )
            engine_task = tres.scalar_one_or_none()
            if engine_task is not None:
                await task_service.reopen_task(db, engine_task)
            await watering_service.recompute_plant(
                db, plant, last_watered_at=prev_at, set_last_watered=True
            )
    elif plant_id:
        result = await db.execute(
            select(Plant)
            .options(selectinload(Plant.taxon).selectinload(Taxon.care_profile))
            .where(Plant.id == plant_id, Plant.household_id == ctx.household.id)
        )
        plant = result.scalar_one_or_none()
        if plant is not None:
            try:
                await watering_service.recompute_plant(db, plant)
            except Exception:
                pass

    await db.commit()


# --- Watering ---


@router.post(
    "/households/{household_id}/plants/{plant_id}/water",
    response_model=WaterResponse,
)
async def water_plant(
    plant_id: uuid.UUID,
    body: WaterRequest,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> WaterResponse:
    result = await db.execute(
        select(Plant)
        .options(selectinload(Plant.taxon).selectinload(Taxon.care_profile))
        .where(Plant.id == plant_id, Plant.household_id == ctx.household.id)
    )
    plant = result.scalar_one_or_none()
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    occurred = body.occurred_at or datetime.now(UTC)
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=UTC)

    event = await timeline_service.create_event(
        db,
        household_id=ctx.household.id,
        event_type="watered",
        plant_id=plant.id,
        actor_user_id=ctx.user.id,
        occurred_at=occurred,
        payload={
            "amount": body.amount,
            "volume_ml": body.volume_ml,
            "notes": body.notes,
        },
    )

    if body.complete_open_water_task:
        from app.modules.tasks.models import Task

        source_key = f"engine:water:{plant.id}"
        tres = await db.execute(
            select(Task)
            .options(selectinload(Task.plant_links))
            .where(
                Task.household_id == ctx.household.id,
                Task.source_key == source_key,
                Task.status == "open",
            )
        )
        task = tres.scalar_one_or_none()
        if task:
            task.status = "done"
            task.completed_at = occurred
            task.completed_by_user_id = ctx.user.id
            event.task_id = task.id

    state, rec = await watering_service.recompute_plant(
        db, plant, last_watered_at=occurred, set_last_watered=True
    )
    await db.commit()
    await db.refresh(event)
    return WaterResponse(
        event=await _event_public(db, event),
        watering=_watering_public(plant.id, state, rec),
    )


@router.get(
    "/households/{household_id}/plants/{plant_id}/watering",
    response_model=WateringPublic,
)
async def get_watering(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> WateringPublic:
    result = await db.execute(
        select(Plant)
        .options(selectinload(Plant.taxon).selectinload(Taxon.care_profile))
        .where(Plant.id == plant_id, Plant.household_id == ctx.household.id)
    )
    plant = result.scalar_one_or_none()
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    state, rec = await watering_service.recompute_plant(db, plant)
    await db.commit()
    return _watering_public(plant.id, state, rec)


@router.post(
    "/households/{household_id}/plants/{plant_id}/watering-feedback",
    response_model=WateringPublic,
)
async def watering_feedback(
    plant_id: uuid.UUID,
    body: FeedbackRequest,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> WateringPublic:
    if body.rating not in {"too_dry", "ok", "too_wet"}:
        raise HTTPException(status_code=422, detail="rating must be too_dry, ok, or too_wet")
    result = await db.execute(
        select(Plant)
        .options(selectinload(Plant.taxon).selectinload(Taxon.care_profile))
        .where(Plant.id == plant_id, Plant.household_id == ctx.household.id)
    )
    plant = result.scalar_one_or_none()
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    state = await watering_service.ensure_watering_state(db, plant=plant)
    await watering_service.apply_feedback(db, state, body.rating)
    state, rec = await watering_service.recompute_plant(db, plant)
    await timeline_service.create_event(
        db,
        household_id=ctx.household.id,
        event_type="note",
        plant_id=plant.id,
        actor_user_id=ctx.user.id,
        payload={"kind": "watering_feedback", "rating": body.rating, "notes": body.notes},
    )
    await db.commit()
    return _watering_public(plant.id, state, rec)


@router.get("/households/{household_id}/watering/due")
async def watering_due(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> list[dict[str, Any]]:
    rows = await watering_service.list_due(db, household_id=ctx.household.id)
    return [
        {
            "plant_id": str(plant.id),
            "nickname": plant.nickname,
            "urgency": state.urgency,
            "next_due_at": state.next_due_at.isoformat() if state.next_due_at else None,
            "recommended_amount": state.recommended_amount,
            "confidence": state.confidence,
        }
        for plant, state in rows
    ]


# --- Tasks ---


@router.get("/households/{household_id}/tasks", response_model=list[TaskPublic])
async def list_tasks(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
    status_filter: str | None = Query("open", alias="status"),
    type: str | None = None,
    limit: int = Query(50, ge=1, le=100),
) -> list[TaskPublic]:
    tasks = await task_service.list_tasks(
        db,
        household_id=ctx.household.id,
        status=status_filter if status_filter != "all" else None,
        task_type=type,
        limit=limit,
    )
    return [_task_public(t) for t in tasks]


@router.post(
    "/households/{household_id}/tasks",
    response_model=TaskPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    body: TaskCreate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> TaskPublic:
    due = body.due_at
    if due is not None and due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    try:
        task = await task_service.create_task(
            db,
            household_id=ctx.household.id,
            created_by=ctx.user.id,
            title=body.title,
            task_type=body.type,
            description=body.description,
            due_at=due,
            priority=body.priority,
            plant_ids=body.plant_ids,
            create_event_on_complete=body.create_event_on_complete,
            event_type_on_complete=body.event_type_on_complete,
            payload=body.payload,
        )
        task_id = task.id
        await db.commit()
        task = await task_service.get_task(
            db, household_id=ctx.household.id, task_id=task_id
        )
        if task is None:
            raise HTTPException(status_code=500, detail="Task created but could not reload")
    except TaskError as exc:
        await db.rollback()
        raise _task_err(exc) from exc
    return _task_public(task)


class BulkActionBody(BaseModel):
    """Optional subset of plant/task ids; empty = all actionable on the dashboard."""

    plant_ids: list[uuid.UUID] | None = None
    task_ids: list[uuid.UUID] | None = None
    amount: str = "normal"


@router.post("/households/{household_id}/bulk/water-all")
async def bulk_water_all(
    body: BulkActionBody,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    """Mark all (or selected) due plants as watered."""
    due_rows = await watering_service.list_due(db, household_id=ctx.household.id)
    want = set(body.plant_ids) if body.plant_ids else None
    done = 0
    for plant, state in due_rows:
        if want is not None and plant.id not in want:
            continue
        amount = body.amount or state.recommended_amount or "normal"
        occurred = datetime.now(UTC)
        await timeline_service.create_event(
            db,
            household_id=ctx.household.id,
            event_type="watered",
            plant_id=plant.id,
            actor_user_id=ctx.user.id,
            occurred_at=occurred,
            payload={"amount": amount, "bulk": True},
        )
        from app.modules.tasks.models import Task

        source_key = f"engine:water:{plant.id}"
        tres = await db.execute(
            select(Task).where(
                Task.household_id == ctx.household.id,
                Task.source_key == source_key,
                Task.status == "open",
            )
        )
        task = tres.scalar_one_or_none()
        if task:
            task.status = "done"
            task.completed_at = occurred
            task.completed_by_user_id = ctx.user.id
        result = await db.execute(
            select(Plant)
            .options(selectinload(Plant.taxon).selectinload(Taxon.care_profile))
            .where(Plant.id == plant.id)
        )
        p = result.scalar_one()
        await watering_service.recompute_plant(
            db, p, last_watered_at=occurred, set_last_watered=True
        )
        done += 1
    await db.commit()
    return {"watered": done, "message": f"Marked {done} plant(s) watered."}


@router.post("/households/{household_id}/bulk/complete-tasks")
async def bulk_complete_tasks(
    body: BulkActionBody,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    """Complete open tasks due today (or selected ids)."""
    now = datetime.now(UTC)
    end_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    open_tasks = await task_service.list_tasks(
        db, household_id=ctx.household.id, status="open", limit=200
    )
    want = set(body.task_ids) if body.task_ids else None
    done = 0
    for task in open_tasks:
        if want is not None and task.id not in want:
            continue
        if want is None and task.due_at is not None and task.due_at > end_today:
            continue  # only due today / overdue when bulk all
        if want is None and task.due_at is None and task.type == "water":
            continue  # skip undated engine noise unless selected
        try:
            await task_service.complete_task(
                db, task, user_id=ctx.user.id, occurred_at=now
            )
            done += 1
        except TaskError:
            continue
    await db.commit()
    return {"completed": done, "message": f"Completed {done} task(s)."}


@router.post("/households/{household_id}/bulk/fertilize-due")
async def bulk_fertilize_due(
    body: BulkActionBody,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict[str, Any]:
    """Complete open fertilize tasks (or log fertilized for selected plants)."""
    now = datetime.now(UTC)
    open_tasks = await task_service.list_tasks(
        db, household_id=ctx.household.id, status="open", limit=200
    )
    fert = [t for t in open_tasks if t.type == "fertilize"]
    want_tasks = set(body.task_ids) if body.task_ids else None
    done = 0
    for task in fert:
        if want_tasks is not None and task.id not in want_tasks:
            continue
        try:
            await task_service.complete_task(
                db, task, user_id=ctx.user.id, occurred_at=now
            )
            done += 1
        except TaskError:
            continue
    # Optional: fertilize selected plants with no open task
    if body.plant_ids:
        for pid in body.plant_ids:
            plant = await db.get(Plant, pid)
            if plant is None or plant.household_id != ctx.household.id:
                continue
            await timeline_service.create_event(
                db,
                household_id=ctx.household.id,
                event_type="fertilized",
                plant_id=pid,
                actor_user_id=ctx.user.id,
                occurred_at=now,
                payload={"bulk": True},
            )
            done += 1
    await db.commit()
    return {"fertilized": done, "message": f"Logged fertilize for {done} item(s)."}


@router.post(
    "/households/{household_id}/tasks/{task_id}/complete",
    response_model=TaskPublic,
)
async def complete_task(
    task_id: uuid.UUID,
    body: TaskComplete,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> TaskPublic:
    task = await task_service.get_task(
        db, household_id=ctx.household.id, task_id=task_id
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        task = await task_service.complete_task(
            db,
            task,
            user_id=ctx.user.id,
            occurred_at=body.occurred_at,
            result_payload=body.result_payload,
        )
        await db.commit()
        task = await task_service.get_task(
            db, household_id=ctx.household.id, task_id=task_id
        )
        assert task is not None
    except TaskError as exc:
        await db.rollback()
        raise _task_err(exc) from exc
    return _task_public(task)


@router.patch(
    "/households/{household_id}/tasks/{task_id}",
    response_model=TaskPublic,
)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> TaskPublic:
    task = await task_service.get_task(
        db, household_id=ctx.household.id, task_id=task_id
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    data = body.model_dump(exclude_unset=True)
    status_val = data.pop("status", None)
    if status_val == "cancelled":
        await task_service.cancel_task(db, task)
    elif status_val == "open" and task.status != "open":
        await task_service.reopen_task(db, task)
    await task_service.update_task(
        db,
        task,
        title=data.get("title"),
        description=data.get("description"),
        due_at=data.get("due_at"),
        clear_due=bool(data.get("clear_due")),
        priority=data.get("priority"),
        task_type=data.get("type"),
    )
    await db.commit()
    task = await task_service.get_task(
        db, household_id=ctx.household.id, task_id=task_id
    )
    assert task is not None
    return _task_public(task)


@router.delete(
    "/households/{household_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
    hard: bool = Query(False, description="Permanently delete instead of cancel"),
) -> None:
    task = await task_service.get_task(
        db, household_id=ctx.household.id, task_id=task_id
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if hard:
        await task_service.hard_delete_task(db, task)
    else:
        await task_service.cancel_task(db, task)
    await db.commit()


# --- Dashboard ---


class DashboardResponse(BaseModel):
    tasks_today: list[TaskPublic]
    attention: list[dict[str, Any]]
    upcoming: list[TaskPublic]
    recent_events: list[EventPublic]
    counts: dict[str, int]
    weather: dict[str, Any] | None = None
    care_brief: dict[str, Any] | None = None
    discover: dict[str, Any] | None = None


@router.get("/households/{household_id}/dashboard", response_model=DashboardResponse)
async def dashboard(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> DashboardResponse:
    now = datetime.now(UTC)
    end_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    week = now + timedelta(days=7)

    # Pull more open tasks then filter — engine schedules far ahead (prune/fertilize)
    open_tasks = await task_service.list_tasks(
        db, household_id=ctx.household.id, status="open", limit=200
    )
    # Actionable "today": due today or overdue (not every future engine task)
    tasks_today = [
        t
        for t in open_tasks
        if t.due_at is not None and t.due_at <= end_today
    ]
    upcoming = [
        t
        for t in open_tasks
        if t.due_at is not None and end_today < t.due_at <= week
    ][:20]
    # Count only due-now + due-this-week (not "all open forever")
    open_actionable = len(tasks_today) + len(upcoming)

    due_rows = await watering_service.list_due(db, household_id=ctx.household.id)
    attention = []
    for p, s in due_rows[:12]:
        try:
            # Fresh care card (amount ml, time of day, weather-aware)
            _, rec = await watering_service.recompute_plant(db, p)
        except Exception:
            rec = None
        attrs = p.custom_attributes or {}
        emoji = attrs.get("emoji") if isinstance(attrs.get("emoji"), str) else None
        heat = False
        dry_air = False
        if rec and rec.weather_note:
            heat = any(k in (rec.weather_note or "").lower() for k in ("hot", "heat", "°c"))
            dry_air = "humidity" in (rec.weather_note or "").lower() and "low" in " ".join(
                f.get("label", "").lower() for f in (rec.factor_breakdown or [])
            )
        if rec:
            for f in rec.factor_breakdown or []:
                lab = (f.get("label") or "").lower()
                if "hot" in lab or "heat" in lab or "very hot" in lab:
                    heat = True
                if "dry air" in lab or "low humidity" in lab:
                    dry_air = True
        attention.append(
            {
                "plant_id": str(p.id),
                "nickname": p.nickname,
                "emoji": (emoji or "🪴")[:8],
                "urgency": (rec.urgency if rec else s.urgency),
                "next_due_at": (
                    rec.next_due_at.isoformat()
                    if rec and rec.next_due_at
                    else (s.next_due_at.isoformat() if s.next_due_at else None)
                ),
                "recommended_amount": rec.recommended_amount if rec else s.recommended_amount,
                "amount_label": getattr(rec, "amount_label", None) if rec else None,
                "amount_ml": getattr(rec, "amount_ml", None) if rec else None,
                "amount_howto": getattr(rec, "amount_howto", None) if rec else None,
                "best_time_label": getattr(rec, "best_time_label", None) if rec else None,
                "best_time_local": getattr(rec, "best_time_local", None) if rec else None,
                "schedule_plain": getattr(rec, "schedule_plain", None) if rec else None,
                "weather_note": getattr(rec, "weather_note", None) if rec else None,
                "interval_days": getattr(rec, "interval_days", None) if rec else None,
                "heat_stress": heat,
                "dry_air": dry_air,
            }
        )

    events = await timeline_service.list_events(
        db, household_id=ctx.household.id, limit=15
    )
    context = await timeline_service.load_event_context(db, events)
    recent = [
        EventPublic(
            id=e.id,
            household_id=e.household_id,
            plant_id=e.plant_id,
            plant_nickname=context["plants"].get(e.plant_id) if e.plant_id else None,
            actor_user_id=e.actor_user_id,
            actor_name=context["actors"].get(e.actor_user_id) if e.actor_user_id else None,
            type=e.type,
            occurred_at=e.occurred_at,
            payload=e.payload or {},
            task_id=e.task_id,
            created_at=e.created_at,
        )
        for e in events
    ]

    from sqlalchemy import func

    plants_active = await db.execute(
        select(func.count())
        .select_from(Plant)
        .where(
            Plant.household_id == ctx.household.id,
            Plant.status.in_(["active", "dormant"]),
        )
    )

    weather = None
    try:
        from app.modules.weather import service as weather_service

        snap = await weather_service.get_household_weather(db, ctx.household)
        pub = weather_service.weather_public(snap)
        weather = {"configured": True, **pub} if pub else {"configured": False}
        if weather.get("configured"):
            await db.commit()
    except Exception:
        weather = {"configured": False}

    care_brief = None
    try:
        from app.modules.stats import service as stats_service

        care_brief = await stats_service.care_brief(db, ctx.household.id)
    except Exception:
        care_brief = None

    plant_count = int(plants_active.scalar_one())
    discover = None
    try:
        from app.modules.stats.discover import build_discover

        discover = build_discover(
            weather=weather if weather and weather.get("configured") else None,
            plant_count=plant_count,
        )
    except Exception:
        discover = None

    # Quietly fill missing plant photos from Wikimedia (species lookalikes)
    try:
        settings = ctx.household.settings or {}
        if settings.get("auto_cover_images", True):
            from app.modules.plants import service as plant_service

            await plant_service.fill_missing_covers(
                db,
                household_id=ctx.household.id,
                user_id=ctx.user.id,
                limit=6,
            )
    except Exception:
        pass

    try:
        await db.commit()
    except Exception:
        pass

    return DashboardResponse(
        tasks_today=[_task_public(t) for t in tasks_today],
        attention=attention,
        upcoming=[_task_public(t) for t in upcoming],
        recent_events=recent,
        counts={
            "plants_active": plant_count,
            "overdue_water": sum(1 for _, s in due_rows if s.urgency == "overdue"),
            "open_tasks": open_actionable,
            "due_soon": sum(1 for _, s in due_rows if s.urgency in {"due", "soon"}),
        },
        weather=weather,
        care_brief=care_brief,
        discover=discover,
    )
