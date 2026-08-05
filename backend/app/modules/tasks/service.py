"""Task services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.plants.models import Plant
from app.modules.tasks.models import Task, TaskPlant
from app.modules.taxonomy.models import Taxon
from app.modules.timeline import service as timeline_service
from app.modules.watering import service as watering_service


class TaskError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


EVENT_TYPE_FOR_TASK = {
    "water": "watered",
    "fertilize": "fertilized",
    "prune": "pruned",
    "repot": "repotted",
    "propagate": "propagated",
    "harvest": "harvested",
    "clean": "cleaned",
}


async def get_task(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    task_id: uuid.UUID,
) -> Task | None:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.plant_links))
        .where(Task.id == task_id, Task.household_id == household_id)
    )
    return result.scalar_one_or_none()


async def list_tasks(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    status: str | None = "open",
    task_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Task]:
    stmt = (
        select(Task)
        .options(selectinload(Task.plant_links))
        .where(Task.household_id == household_id)
    )
    if status:
        stmt = stmt.where(Task.status == status)
    if task_type:
        stmt = stmt.where(Task.type == task_type)
    stmt = stmt.order_by(Task.due_at.asc().nulls_last(), Task.created_at.desc())
    stmt = stmt.limit(min(limit, 100)).offset(max(offset, 0))
    result = await db.execute(stmt)
    return list(result.scalars())


async def create_task(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    created_by: uuid.UUID | None,
    title: str,
    task_type: str = "custom",
    description: str | None = None,
    due_at: datetime | None = None,
    priority: str = "normal",
    plant_ids: list[uuid.UUID] | None = None,
    create_event_on_complete: bool = True,
    event_type_on_complete: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Task:
    task = Task(
        household_id=household_id,
        title=title.strip(),
        description=description,
        type=task_type,
        status="open",
        priority=priority,
        due_at=due_at,
        source="user",
        create_event_on_complete=create_event_on_complete,
        event_type_on_complete=event_type_on_complete or EVENT_TYPE_FOR_TASK.get(task_type),
        payload=payload or {},
        created_by_user_id=created_by,
    )
    db.add(task)
    await db.flush()
    for pid in plant_ids or []:
        # verify plant belongs to household
        result = await db.execute(
            select(Plant.id).where(Plant.id == pid, Plant.household_id == household_id)
        )
        if result.scalar_one_or_none() is None:
            raise TaskError("Plant not found in household", status_code=404)
        db.add(TaskPlant(task_id=task.id, plant_id=pid))
    await db.flush()
    return await get_task(db, household_id=household_id, task_id=task.id)  # type: ignore[return-value]


async def complete_task(
    db: AsyncSession,
    task: Task,
    *,
    user_id: uuid.UUID,
    occurred_at: datetime | None = None,
    result_payload: dict[str, Any] | None = None,
) -> Task:
    if task.status == "done":
        return task

    now = occurred_at or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    task.status = "done"
    task.completed_at = now
    task.completed_by_user_id = user_id
    await db.flush()

    plant_ids = [link.plant_id for link in task.plant_links]
    event_type = task.event_type_on_complete or EVENT_TYPE_FOR_TASK.get(task.type)

    if task.create_event_on_complete and event_type:
        payload = {**(task.payload or {}), **(result_payload or {})}
        if not plant_ids:
            await timeline_service.create_event(
                db,
                household_id=task.household_id,
                event_type=event_type,
                actor_user_id=user_id,
                occurred_at=now,
                payload=payload,
                task_id=task.id,
            )
        for pid in plant_ids:
            await timeline_service.create_event(
                db,
                household_id=task.household_id,
                event_type=event_type,
                plant_id=pid,
                actor_user_id=user_id,
                occurred_at=now,
                payload=payload,
                task_id=task.id,
            )
            if event_type == "watered":
                result = await db.execute(
                    select(Plant)
                    .options(selectinload(Plant.taxon).selectinload(Taxon.care_profile))
                    .where(Plant.id == pid)
                )
                plant = result.scalar_one_or_none()
                if plant:
                    await watering_service.recompute_plant(
                        db, plant, last_watered_at=now, set_last_watered=True
                    )

    await db.flush()
    return task


async def cancel_task(db: AsyncSession, task: Task) -> Task:
    task.status = "cancelled"
    await db.flush()
    return task


async def hard_delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.flush()


async def update_task(
    db: AsyncSession,
    task: Task,
    *,
    title: str | None = None,
    description: str | None = None,
    due_at: datetime | None = None,
    clear_due: bool = False,
    priority: str | None = None,
    task_type: str | None = None,
) -> Task:
    if title is not None:
        task.title = title.strip()
    if description is not None:
        task.description = description
    if clear_due:
        task.due_at = None
    elif due_at is not None:
        task.due_at = due_at
    if priority is not None:
        task.priority = priority
    if task_type is not None:
        task.type = task_type
    await db.flush()
    return task


async def reopen_task(db: AsyncSession, task: Task) -> Task:
    task.status = "open"
    task.completed_at = None
    task.completed_by_user_id = None
    await db.flush()
    return task
