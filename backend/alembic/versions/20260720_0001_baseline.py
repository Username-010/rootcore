"""baseline empty schema

Revision ID: 20260720_0001
Revises:
Create Date: 2026-07-20

Baseline revision — tables arrive with identity/plants features.
Ensures Alembic is wired and the database is migration-ready.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "20260720_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No tables yet — foundation phase only.
    pass


def downgrade() -> None:
    pass
