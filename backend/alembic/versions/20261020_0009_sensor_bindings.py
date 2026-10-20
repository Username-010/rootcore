"""Add plant sensor bindings without modifying existing plant data."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261020_0009"
down_revision = "20260720_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sensor_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "household_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("households.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("adapter_id", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(208), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("household_id", "plant_id", "entity_id", name="uq_sensor_binding"),
    )
    op.create_index("ix_sensor_bindings_household_id", "sensor_bindings", ["household_id"])
    op.create_index("ix_sensor_bindings_plant_id", "sensor_bindings", ["plant_id"])


def downgrade():
    op.drop_table("sensor_bindings")
