"""Plant schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.taxonomy.schemas import TaxonPublic

PlantStatus = Literal["active", "dormant", "deceased", "archived"]
Environment = Literal["indoor", "outdoor", "greenhouse"]


class TagPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str | None = None


class PhotoPublic(BaseModel):
    id: uuid.UUID
    plant_id: uuid.UUID
    caption: str | None
    taken_at: datetime | None
    mime_type: str
    byte_size: int
    width: int | None
    height: int | None
    thumb_url: str | None
    display_url: str | None
    original_url: str | None
    created_at: datetime
    is_cover: bool = False


class PlantListItem(BaseModel):
    id: uuid.UUID
    nickname: str
    status: str
    environment: str
    taxon: TaxonPublic | None = None
    cover_photo: PhotoPublic | None = None
    tags: list[TagPublic] = Field(default_factory=list)
    pot_size_liters: float | None = None
    acquired_at: date | None = None
    created_at: datetime
    emoji: str | None = None
    custom_attributes: dict[str, Any] = Field(default_factory=dict)


class PlantDetail(PlantListItem):
    pot_material: str | None = None
    soil_type: str | None = None
    growth_stage: str | None = None
    estimated_value: float | None = None
    notes: str | None = None
    custom_attributes: dict[str, Any] = Field(default_factory=dict)
    deceased_at: date | None = None
    deceased_reason: str | None = None
    archived_at: datetime | None = None
    created_by_user_id: uuid.UUID | None = None
    updated_at: datetime


class PlantCreate(BaseModel):
    nickname: str = Field(min_length=1, max_length=200)
    taxon_id: uuid.UUID | None = None
    status: PlantStatus = "active"
    # None → infer from species (garden plants → outdoor)
    environment: Environment | None = None
    acquired_at: date | None = None
    pot_size_liters: float | None = Field(default=None, gt=0)
    pot_material: str | None = None
    soil_type: str | None = None
    growth_stage: str | None = None
    estimated_value: float | None = Field(default=None, ge=0)
    notes: str | None = None
    tag_names: list[str] = Field(default_factory=list)
    custom_attributes: dict[str, Any] = Field(default_factory=dict)
    # Optional care extras on create
    last_fertilized_at: date | None = None
    # Fetch free Wikimedia cover when household allows (default True if unset)
    auto_cover_image: bool | None = None


class PlantUpdate(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=200)
    taxon_id: uuid.UUID | None = None
    status: PlantStatus | None = None
    environment: Environment | None = None
    acquired_at: date | None = None
    pot_size_liters: float | None = Field(default=None, gt=0)
    pot_material: str | None = None
    soil_type: str | None = None
    growth_stage: str | None = None
    estimated_value: float | None = Field(default=None, ge=0)
    notes: str | None = None
    tag_names: list[str] | None = None
    custom_attributes: dict[str, Any] | None = None


class DeceaseRequest(BaseModel):
    deceased_at: date | None = None
    reason: str | None = None


class PaginatedPlants(BaseModel):
    items: list[PlantListItem]
    total: int
    limit: int
    offset: int


class PhotoUpdate(BaseModel):
    caption: str | None = None
    taken_at: datetime | None = None
