"""Plant specimen ORM models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.taxonomy.models import Taxon


class Plant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "plants"

    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    taxon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxa.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nickname: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    environment: Mapped[str] = mapped_column(String(32), nullable=False, default="indoor")
    acquired_at: Mapped[date | None] = mapped_column(Date)
    propagated_from_plant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="SET NULL"),
        nullable=True,
    )
    pot_size_liters: Mapped[float | None] = mapped_column(Float)
    pot_material: Mapped[str | None] = mapped_column(String(64))
    soil_type: Mapped[str | None] = mapped_column(String(64))
    growth_stage: Mapped[str | None] = mapped_column(String(64))
    estimated_value: Mapped[float | None] = mapped_column(Float)
    cover_photo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    custom_attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    notes: Mapped[str | None] = mapped_column(Text)
    deceased_at: Mapped[date | None] = mapped_column(Date)
    deceased_reason: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    taxon: Mapped[Taxon | None] = relationship(lazy="selectin")
    photos: Mapped[list[PlantPhoto]] = relationship(
        back_populates="plant",
        cascade="all, delete-orphan",
        foreign_keys="PlantPhoto.plant_id",
    )
    tag_links: Mapped[list[PlantTag]] = relationship(
        back_populates="plant",
        cascade="all, delete-orphan",
    )


class Tag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("household_id", "name", name="uq_tags_household_name"),)

    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str | None] = mapped_column(String(32))


class PlantTag(Base):
    __tablename__ = "plant_tags"

    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    plant: Mapped[Plant] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(lazy="selectin")


class PlantPhoto(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "plant_photos"

    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    thumb_key: Mapped[str | None] = mapped_column(Text)
    display_key: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(Text)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    plant: Mapped[Plant] = relationship(
        back_populates="photos",
        foreign_keys=[plant_id],
    )
