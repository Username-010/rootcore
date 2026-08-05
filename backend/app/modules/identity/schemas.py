"""Identity request/response schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Username or email — no real mailbox required for self-host
_LOGIN_RE = re.compile(r"^[a-zA-Z0-9._@+\-]{2,120}$")


def _normalize_login(value: str) -> str:
    v = value.strip()
    if not v or not _LOGIN_RE.match(v):
        raise ValueError(
            "Use a username (letters, numbers, . _ -) or an email address (2–120 chars)"
        )
    return v.lower()


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str  # login id: username or email
    display_name: str
    timezone: str
    locale: str
    unit_system: str
    theme: str
    is_instance_admin: bool
    created_at: datetime


class RegisterRequest(BaseModel):
    email: str = Field(
        min_length=2,
        max_length=120,
        description="Username or email — either works as your login",
    )
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="UTC", max_length=64)

    @field_validator("email")
    @classmethod
    def validate_login(cls, v: str) -> str:
        return _normalize_login(v)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=120, description="Username or email")
    password: str
    client: Literal["web", "api"] = "api"

    @field_validator("email")
    @classmethod
    def validate_login(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class SetupRequest(BaseModel):
    email: str = Field(
        min_length=2,
        max_length=120,
        description="Username or email for admin login",
    )
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    household_name: str = Field(min_length=1, max_length=200)
    timezone: str = Field(default="UTC", max_length=64)
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("email")
    @classmethod
    def validate_login(cls, v: str) -> str:
        return _normalize_login(v)


class SetupResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic
    household_id: uuid.UUID
    household_name: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=16)
    unit_system: Literal["metric", "imperial"] | None = None
    theme: Literal["system", "light", "dark"] | None = None


class MessageResponse(BaseModel):
    message: str
