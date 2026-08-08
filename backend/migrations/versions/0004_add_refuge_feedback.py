"""Add anonymous refuge-specific community feedback.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refuge_feedback",
        sa.Column("feedback_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("refuge_id", sa.BigInteger(), nullable=False),
        sa.Column("quietness_score", sa.SmallInteger(), nullable=False),
        sa.Column("crowding_level", sa.String(length=20), nullable=False),
        sa.Column("comfort_level", sa.String(length=20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quietness_score BETWEEN 1 AND 5", name="ck_refuge_feedback_quietness_range"),
        sa.CheckConstraint("crowding_level IN ('low', 'moderate', 'high')", name="ck_refuge_feedback_crowding_level"),
        sa.CheckConstraint("comfort_level IN ('yes', 'somewhat', 'no')", name="ck_refuge_feedback_comfort_level"),
        sa.ForeignKeyConstraint(
            ["refuge_id"],
            ["point_of_interest.poi_id"],
            name="fk_refuge_feedback_refuge_id_point_of_interest",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("feedback_id"),
    )
    op.create_index("ix_refuge_feedback_refuge_id", "refuge_feedback", ["refuge_id"])
    op.create_index("ix_refuge_feedback_refuge_id_created_at", "refuge_feedback", ["refuge_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_refuge_feedback_refuge_id_created_at", table_name="refuge_feedback")
    op.drop_index("ix_refuge_feedback_refuge_id", table_name="refuge_feedback")
    op.drop_table("refuge_feedback")
