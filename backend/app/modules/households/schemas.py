"""Household request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["owner", "admin", "member", "viewer"]


class HouseholdPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str | None
    timezone: str
    currency: str
    latitude: float | None
    longitude: float | None
    settings: dict[str, Any]
    role: Role | None = None
    created_at: datetime


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    timezone: str = Field(default="UTC", max_length=64)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    latitude: float | None = None
    longitude: float | None = None


class HouseholdUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    timezone: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    latitude: float | None = None
    longitude: float | None = None
    settings: dict[str, Any] | None = None
    # Convenience flags merged into settings when provided
    auto_cover_images: bool | None = None
    plantnet_api_key: str | None = None
    weather_provider: Literal["open_meteo", "met_norway"] | None = None
    plant_id_provider: Literal["plantnet", "none"] | None = None


class MemberPublic(BaseModel):
    user_id: uuid.UUID
    email: str  # login id (username or email)
    display_name: str
    role: Role
    joined_at: datetime


class MemberRoleUpdate(BaseModel):
    role: Role


class InvitationCreate(BaseModel):
    email: str | None = None
    role: Role = "member"
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationPublic(BaseModel):
    id: uuid.UUID
    email: str | None
    role: Role
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    # Only returned on create
    token: str | None = None
    invite_url_path: str | None = None


class AcceptInvitationRequest(BaseModel):
    token: str = Field(min_length=10)
