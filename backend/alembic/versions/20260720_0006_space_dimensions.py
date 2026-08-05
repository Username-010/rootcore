"""space real-world dimensions for garden maps

Revision ID: 20260720_0006
Revises: 20260720_0005
Create Date: 2026-07-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260720_0006"
down_revision: Union[str, None] = "20260720_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("spaces", sa.Column("length_m", sa.Float(), nullable=True))
    op.add_column("spaces", sa.Column("width_m", sa.Float(), nullable=True))
    op.add_column(
        "spaces",
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("spaces", "notes")
    op.drop_column("spaces", "width_m")
    op.drop_column("spaces", "length_m")
