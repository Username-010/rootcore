"""Watering state cache ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WateringState(Base):
    __tablename__ = "watering_states"

    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    urgency: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    recommended_amount: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(Float)
    moisture_score: Mapped[float | None] = mapped_column(Float)
    factor_breakdown: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    interval_bias_days: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    threshold_bias: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_watered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manual_next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    feedback_counts: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=lambda: {"too_dry": 0, "ok": 0, "too_wet": 0}
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
