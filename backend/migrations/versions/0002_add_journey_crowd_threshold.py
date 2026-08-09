"""Store the crowd preference used for each planned journey.

Revision ID: 0002_add_journey_crowd_threshold
Revises: 0001_create_initial_escape_tables
Create Date: 2026-08-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "journey_request",
        sa.Column("preferred_crowd_threshold", sa.SmallInteger(), server_default="3", nullable=False),
    )
    op.create_check_constraint(
        "ck_journey_request_preferred_crowd_threshold_range",
        "journey_request",
        "preferred_crowd_threshold BETWEEN 1 AND 5",
    )
    op.alter_column("journey_request", "preferred_crowd_threshold", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_journey_request_preferred_crowd_threshold_range",
        "journey_request",
        type_="check",
    )
    op.drop_column("journey_request", "preferred_crowd_threshold")
