"""container emoji for map markers

Revision ID: 20260720_0008
Revises: 20260720_0007
Create Date: 2026-07-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260720_0008"
down_revision: Union[str, None] = "20260720_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "containers",
        sa.Column("emoji", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("containers", "emoji")
