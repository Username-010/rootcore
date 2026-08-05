"""Taxonomy schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CareProfilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    light: str | None = None
    moisture_preference: str | None = None
    drought_tolerance: str | None = None
    humidity_preference: str | None = None
    baseline_interval_days_min: float | None = None
    baseline_interval_days_max: float | None = None
    water_amount_default: str | None = None
    fertilize_notes: str | None = None
    soil_notes: str | None = None
    toxic_to_pets: bool | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class TaxonPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    rank: str
    scientific_name: str
    authors: str | None
    common_names: list[str]
    family: str | None
    genus: str | None
    care_profile: CareProfilePublic | None = None
    created_at: datetime


class TaxonCreate(BaseModel):
    scientific_name: str = Field(min_length=1, max_length=255)
    common_names: list[str] = Field(default_factory=list)
    rank: str = "species"
    family: str | None = None
    genus: str | None = None
    parent_id: uuid.UUID | None = None
    care_profile: CareProfilePublic | None = None
