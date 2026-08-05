"""plants taxonomy photos

Revision ID: 20260720_0003
Revises: 20260720_0002
Create Date: 2026-07-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260720_0003"
down_revision: Union[str, None] = "20260720_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "taxa",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("rank", sa.String(length=32), nullable=False),
        sa.Column("scientific_name", sa.String(length=255), nullable=False),
        sa.Column("authors", sa.String(length=255), nullable=True),
        sa.Column("common_names", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("family", sa.String(length=120), nullable=True),
        sa.Column("genus", sa.String(length=120), nullable=True),
        sa.Column(
            "external_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["taxa.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_taxa_household_id", "taxa", ["household_id"])
    op.create_index("ix_taxa_scientific_name", "taxa", ["scientific_name"])
    op.create_index("ix_taxa_genus", "taxa", ["genus"])

    op.create_table(
        "care_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("taxon_id", sa.UUID(), nullable=False),
        sa.Column("light", sa.String(length=64), nullable=True),
        sa.Column("moisture_preference", sa.String(length=64), nullable=True),
        sa.Column("drought_tolerance", sa.String(length=64), nullable=True),
        sa.Column("humidity_preference", sa.String(length=64), nullable=True),
        sa.Column("baseline_interval_days_min", sa.Float(), nullable=True),
        sa.Column("baseline_interval_days_max", sa.Float(), nullable=True),
        sa.Column("water_amount_default", sa.String(length=32), nullable=True),
        sa.Column("fertilize_notes", sa.Text(), nullable=True),
        sa.Column("soil_notes", sa.Text(), nullable=True),
        sa.Column("toxic_to_pets", sa.Boolean(), nullable=True),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["taxon_id"], ["taxa.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("taxon_id", name="uq_care_profiles_taxon_id"),
    )

    op.create_table(
        "plants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("taxon_id", sa.UUID(), nullable=True),
        sa.Column("nickname", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("acquired_at", sa.Date(), nullable=True),
        sa.Column("propagated_from_plant_id", sa.UUID(), nullable=True),
        sa.Column("pot_size_liters", sa.Float(), nullable=True),
        sa.Column("pot_material", sa.String(length=64), nullable=True),
        sa.Column("soil_type", sa.String(length=64), nullable=True),
        sa.Column("growth_stage", sa.String(length=64), nullable=True),
        sa.Column("estimated_value", sa.Float(), nullable=True),
        sa.Column("cover_photo_id", sa.UUID(), nullable=True),
        sa.Column(
            "custom_attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deceased_at", sa.Date(), nullable=True),
        sa.Column("deceased_reason", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["taxon_id"], ["taxa.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["propagated_from_plant_id"], ["plants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plants_household_id", "plants", ["household_id"])
    op.create_index("ix_plants_taxon_id", "plants", ["taxon_id"])

    op.create_table(
        "tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "name", name="uq_tags_household_name"),
    )
    op.create_index("ix_tags_household_id", "tags", ["household_id"])

    op.create_table(
        "plant_tags",
        sa.Column("plant_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plant_id", "tag_id"),
    )

    op.create_table(
        "plant_photos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("household_id", sa.UUID(), nullable=False),
        sa.Column("plant_id", sa.UUID(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("thumb_key", sa.Text(), nullable=True),
        sa.Column("display_key", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plant_photos_household_id", "plant_photos", ["household_id"])
    op.create_index("ix_plant_photos_plant_id", "plant_photos", ["plant_id"])


def downgrade() -> None:
    op.drop_table("plant_photos")
    op.drop_table("plant_tags")
    op.drop_table("tags")
    op.drop_index("ix_plants_taxon_id", table_name="plants")
    op.drop_index("ix_plants_household_id", table_name="plants")
    op.drop_table("plants")
    op.drop_table("care_profiles")
    op.drop_index("ix_taxa_genus", table_name="taxa")
    op.drop_index("ix_taxa_scientific_name", table_name="taxa")
    op.drop_index("ix_taxa_household_id", table_name="taxa")
    op.drop_table("taxa")
