"""Taxonomy ORM models."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Taxon(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "taxa"

    household_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxa.id", ondelete="SET NULL"),
        nullable=True,
    )
    rank: Mapped[str] = mapped_column(String(32), nullable=False, default="species")
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    authors: Mapped[str | None] = mapped_column(String(255))
    common_names: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    family: Mapped[str | None] = mapped_column(String(120))
    genus: Mapped[str | None] = mapped_column(String(120), index=True)
    external_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    care_profile: Mapped[CareProfile | None] = relationship(
        back_populates="taxon",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CareProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "care_profiles"
    __table_args__ = (UniqueConstraint("taxon_id", name="uq_care_profiles_taxon_id"),)

    taxon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxa.id", ondelete="CASCADE"),
        nullable=False,
    )
    light: Mapped[str | None] = mapped_column(String(64))
    moisture_preference: Mapped[str | None] = mapped_column(String(64))
    drought_tolerance: Mapped[str | None] = mapped_column(String(64))
    humidity_preference: Mapped[str | None] = mapped_column(String(64))
    baseline_interval_days_min: Mapped[float | None] = mapped_column(Float)
    baseline_interval_days_max: Mapped[float | None] = mapped_column(Float)
    water_amount_default: Mapped[str | None] = mapped_column(String(32))
    fertilize_notes: Mapped[str | None] = mapped_column(Text)
    soil_notes: Mapped[str | None] = mapped_column(Text)
    toxic_to_pets: Mapped[bool | None] = mapped_column(Boolean)
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    taxon: Mapped[Taxon] = relationship(back_populates="care_profile")
