"""Add Iteration 3 refuge metadata and predictive alerts.

Revision ID: 0003
Revises: 0002_add_journey_crowd_threshold
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("historical_pedestrian_count", sa.Column("data_source", sa.String(length=255), nullable=True))
    op.add_column("realtime_pedestrian_count", sa.Column("data_source", sa.String(length=255), nullable=True))

    op.add_column("point_of_interest", sa.Column("source_record_id", sa.String(length=255), nullable=True))
    op.add_column("point_of_interest", sa.Column("accessibility_notes", sa.Text(), nullable=True))
    op.add_column("point_of_interest", sa.Column("sensory_notes", sa.Text(), nullable=True))
    op.create_unique_constraint(
        "uq_point_of_interest_source_record_id",
        "point_of_interest",
        ["source", "source_record_id"],
    )

    op.create_table(
        "sensory_prediction",
        sa.Column("prediction_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("sensor_id", sa.BigInteger(), nullable=False),
        sa.Column("prediction_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_count", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_freshness", sa.String(length=20), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("data_availability_status", sa.String(length=30), nullable=False),
        sa.Column("limitation_message", sa.Text(), nullable=True),
        sa.Column("source_validated", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sensor_id"],
            ["sensor_location.sensor_id"],
            name="fk_sensory_prediction_sensor_id_sensor_location",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("prediction_id"),
        sa.UniqueConstraint(
            "sensor_id",
            "prediction_for",
            "model_version",
            name="uq_sensory_prediction_sensor_target_model",
        ),
    )
    op.create_index("ix_sensory_prediction_prediction_for", "sensory_prediction", ["prediction_for"])
    op.create_index("ix_sensory_prediction_sensor_id", "sensory_prediction", ["sensor_id"])

    op.alter_column("alert", "route_id", existing_type=sa.BigInteger(), nullable=True)
    op.add_column("alert", sa.Column("prediction_id", sa.BigInteger(), nullable=True))
    op.add_column("alert", sa.Column("deduplication_key", sa.String(length=255), nullable=True))
    op.add_column("alert", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_alert_prediction_id_sensory_prediction",
        "alert",
        "sensory_prediction",
        ["prediction_id"],
        ["prediction_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_alert_deduplication_key", "alert", ["deduplication_key"])


def downgrade() -> None:
    op.drop_index("ix_alert_deduplication_key", table_name="alert")
    op.drop_constraint("fk_alert_prediction_id_sensory_prediction", "alert", type_="foreignkey")
    op.drop_column("alert", "updated_at")
    op.drop_column("alert", "deduplication_key")
    op.drop_column("alert", "prediction_id")
    op.alter_column("alert", "route_id", existing_type=sa.BigInteger(), nullable=False)
    op.drop_index("ix_sensory_prediction_sensor_id", table_name="sensory_prediction")
    op.drop_index("ix_sensory_prediction_prediction_for", table_name="sensory_prediction")
    op.drop_table("sensory_prediction")
    op.drop_constraint("uq_point_of_interest_source_record_id", "point_of_interest", type_="unique")
    op.drop_column("point_of_interest", "sensory_notes")
    op.drop_column("point_of_interest", "accessibility_notes")
    op.drop_column("point_of_interest", "source_record_id")
    op.drop_column("realtime_pedestrian_count", "data_source")
    op.drop_column("historical_pedestrian_count", "data_source")
