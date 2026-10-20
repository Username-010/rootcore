"""Bindings contain identifiers only; credentials are deployment secrets."""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SensorBinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sensor_bindings"
    __table_args__ = (
        UniqueConstraint("household_id", "plant_id", "entity_id", name="uq_sensor_binding"),
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plants.id", ondelete="CASCADE"), index=True
    )
    adapter_id: Mapped[str] = mapped_column(String(64), default="home_assistant")
    entity_id: Mapped[str] = mapped_column(String(208))
