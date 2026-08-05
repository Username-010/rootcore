"""Timeline schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    type: str = Field(min_length=1, max_length=64)
    plant_id: uuid.UUID | None = None
    occurred_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventUpdate(BaseModel):
    type: str | None = Field(default=None, min_length=1, max_length=64)
    plant_id: uuid.UUID | None = None
    clear_plant: bool = False
    occurred_at: datetime | None = None
    payload: dict[str, Any] | None = None
    notes: str | None = None


class EventPublic(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    plant_id: uuid.UUID | None
    plant_nickname: str | None = None
    actor_user_id: uuid.UUID | None
    actor_name: str | None = None
    type: str
    occurred_at: datetime
    payload: dict[str, Any]
    task_id: uuid.UUID | None
    created_at: datetime


class WaterRequest(BaseModel):
    occurred_at: datetime | None = None
    amount: str = "normal"
    volume_ml: float | None = None
    notes: str | None = None
    complete_open_water_task: bool = True


class WateringPublic(BaseModel):
    plant_id: uuid.UUID
    next_due_at: datetime | None
    urgency: str
    recommended_amount: str | None
    confidence: float | None
    moisture_score: float | None
    last_watered_at: datetime | None
    paused_until: datetime | None
    manual_next_due_at: datetime | None
    factors: list[dict[str, Any]]
    explanation: str | None = None
    # Clear care-card fields
    amount_label: str | None = None
    amount_howto: str | None = None
    amount_ml: int | None = None
    volume_guide: str | None = None
    best_time_of_day: str | None = None
    best_time_label: str | None = None
    best_time_local: str | None = None
    schedule_plain: str | None = None
    weather_note: str | None = None
    interval_days: float | None = None
    advice: dict[str, Any] | None = None


class WaterResponse(BaseModel):
    event: EventPublic
    watering: WateringPublic


class FeedbackRequest(BaseModel):
    rating: str  # too_dry | ok | too_wet
    related_event_id: uuid.UUID | None = None
    notes: str | None = None
