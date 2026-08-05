"""Task schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TaskType = Literal[
    "water", "prune", "repot", "propagate", "harvest", "clean", "fertilize", "custom"
]
TaskStatus = Literal["open", "done", "cancelled"]
Priority = Literal["low", "normal", "high"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    type: TaskType = "custom"
    description: str | None = None
    due_at: datetime | None = None
    priority: Priority = "normal"
    plant_ids: list[uuid.UUID] = Field(default_factory=list)
    create_event_on_complete: bool = True
    event_type_on_complete: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    type: TaskType | None = None
    description: str | None = None
    due_at: datetime | None = None
    clear_due: bool = False
    priority: Priority | None = None
    status: TaskStatus | None = None


class TaskComplete(BaseModel):
    occurred_at: datetime | None = None
    result_payload: dict[str, Any] = Field(default_factory=dict)


class TaskPublic(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    title: str
    description: str | None
    type: str
    status: str
    priority: str
    due_at: datetime | None
    completed_at: datetime | None
    completed_by_user_id: uuid.UUID | None
    assignee_user_id: uuid.UUID | None
    source: str
    plant_ids: list[uuid.UUID]
    payload: dict[str, Any]
    created_at: datetime
