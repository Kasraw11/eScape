"""Create initial eScape tables

Revision ID: 0001_create_initial_escape_tables
Revises:
Create Date: 2026-08-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_preference",
        sa.Column("preference_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preferred_crowd_threshold", sa.SmallInteger(), nullable=False),
        sa.Column("notifications_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("search_radius_m", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "preferred_crowd_threshold BETWEEN 1 AND 5",
            name="ck_user_preference_preferred_crowd_threshold_range",
        ),
        sa.CheckConstraint("search_radius_m > 0", name="ck_user_preference_search_radius_m_positive"),
        sa.PrimaryKeyConstraint("preference_id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_user_preference_session_id", "user_preference", ["session_id"])

    op.create_table(
        "sensor_location",
        sa.Column("sensor_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("sensor_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column("location_type", sa.String(length=50), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("installation_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("direction_1", sa.String(length=100), nullable=True),
        sa.Column("direction_2", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_sensor_location_latitude_range"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_sensor_location_longitude_range"),
        sa.PrimaryKeyConstraint("sensor_id"),
    )
    op.create_index(
        "ix_sensor_location_latitude_longitude",
        "sensor_location",
        ["latitude", "longitude"],
    )

    op.create_table(
        "point_of_interest",
        sa.Column("poi_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("theme", sa.String(length=100), nullable=True),
        sa.Column("sub_theme", sa.String(length=100), nullable=True),
        sa.Column("feature_name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("coordinates_text", sa.Text(), nullable=True),
        sa.Column("opening_hours", sa.Text(), nullable=True),
        sa.Column("is_sensory_refuge", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_point_of_interest_latitude_range"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_point_of_interest_longitude_range"),
        sa.PrimaryKeyConstraint("poi_id"),
    )
    op.create_index(
        "ix_point_of_interest_latitude_longitude",
        "point_of_interest",
        ["latitude", "longitude"],
    )

    op.create_table(
        "transport_stop",
        sa.Column("stop_id", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=30), nullable=False),
        sa.Column("stop_name", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_transport_stop_latitude_range"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_transport_stop_longitude_range"),
        sa.PrimaryKeyConstraint("stop_id"),
    )
    op.create_index(
        "ix_transport_stop_latitude_longitude",
        "transport_stop",
        ["latitude", "longitude"],
    )

    op.create_table(
        "journey_request",
        sa.Column("journey_request_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("preference_id", sa.BigInteger(), nullable=True),
        sa.Column("origin_latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("origin_longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("destination_latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("destination_longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("travel_mode", sa.String(length=30), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "origin_latitude BETWEEN -90 AND 90",
            name="ck_journey_request_origin_latitude_range",
        ),
        sa.CheckConstraint(
            "origin_longitude BETWEEN -180 AND 180",
            name="ck_journey_request_origin_longitude_range",
        ),
        sa.CheckConstraint(
            "destination_latitude BETWEEN -90 AND 90",
            name="ck_journey_request_destination_latitude_range",
        ),
        sa.CheckConstraint(
            "destination_longitude BETWEEN -180 AND 180",
            name="ck_journey_request_destination_longitude_range",
        ),
        sa.ForeignKeyConstraint(
            ["preference_id"],
            ["user_preference.preference_id"],
            name="fk_journey_request_preference_id_user_preference",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("journey_request_id"),
    )
    op.create_index("ix_journey_request_preference_id", "journey_request", ["preference_id"])

    op.create_table(
        "historical_pedestrian_count",
        sa.Column("historical_count_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("sensor_id", sa.BigInteger(), nullable=False),
        sa.Column("sensing_date", sa.Date(), nullable=False),
        sa.Column("hour_of_day", sa.SmallInteger(), nullable=False),
        sa.Column("direction_1_count", sa.Integer(), nullable=True),
        sa.Column("direction_2_count", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "direction_1_count IS NULL OR direction_1_count >= 0",
            name="ck_historical_pedestrian_count_direction_1_non_negative",
        ),
        sa.CheckConstraint(
            "direction_2_count IS NULL OR direction_2_count >= 0",
            name="ck_historical_pedestrian_count_direction_2_non_negative",
        ),
        sa.CheckConstraint(
            "hour_of_day BETWEEN 0 AND 23",
            name="ck_historical_pedestrian_count_hour_of_day_range",
        ),
        sa.CheckConstraint("total_count >= 0", name="ck_historical_pedestrian_count_total_non_negative"),
        sa.ForeignKeyConstraint(
            ["sensor_id"],
            ["sensor_location.sensor_id"],
            name="fk_historical_pedestrian_count_sensor_id_sensor_location",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("historical_count_id"),
        sa.UniqueConstraint(
            "sensor_id",
            "sensing_date",
            "hour_of_day",
            name="uq_historical_pedestrian_count_sensor_date_hour",
        ),
    )
    op.create_index(
        "ix_historical_pedestrian_count_sensor_date_hour",
        "historical_pedestrian_count",
        ["sensor_id", "sensing_date", "hour_of_day"],
    )
    op.create_index(
        "ix_historical_pedestrian_count_sensor_id",
        "historical_pedestrian_count",
        ["sensor_id"],
    )

    op.create_table(
        "realtime_pedestrian_count",
        sa.Column("realtime_count_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("sensor_id", sa.BigInteger(), nullable=False),
        sa.Column("sensed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction_1_count", sa.Integer(), nullable=True),
        sa.Column("direction_2_count", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "direction_1_count IS NULL OR direction_1_count >= 0",
            name="ck_realtime_pedestrian_count_direction_1_non_negative",
        ),
        sa.CheckConstraint(
            "direction_2_count IS NULL OR direction_2_count >= 0",
            name="ck_realtime_pedestrian_count_direction_2_non_negative",
        ),
        sa.CheckConstraint("total_count >= 0", name="ck_realtime_pedestrian_count_total_non_negative"),
        sa.ForeignKeyConstraint(
            ["sensor_id"],
            ["sensor_location.sensor_id"],
            name="fk_realtime_pedestrian_count_sensor_id_sensor_location",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("realtime_count_id"),
    )
    op.create_index(
        "ix_realtime_pedestrian_count_sensor_id",
        "realtime_pedestrian_count",
        ["sensor_id"],
    )
    op.create_index(
        "ix_realtime_pedestrian_count_sensor_id_sensed_at",
        "realtime_pedestrian_count",
        ["sensor_id", "sensed_at"],
    )

    op.create_table(
        "route_option",
        sa.Column("route_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("journey_request_id", sa.BigInteger(), nullable=False),
        sa.Column("google_route_id", sa.String(length=255), nullable=True),
        sa.Column("encoded_polyline", sa.Text(), nullable=True),
        sa.Column("estimated_travel_minutes", sa.Integer(), nullable=False),
        sa.Column("sensory_indicator", sa.String(length=20), nullable=False),
        sa.Column("total_sensory_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("data_availability_status", sa.String(length=30), nullable=False),
        sa.Column("is_recommended", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["journey_request_id"],
            ["journey_request.journey_request_id"],
            name="fk_route_option_journey_request_id_journey_request",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("route_id"),
    )
    op.create_index("ix_route_option_journey_request_id", "route_option", ["journey_request_id"])

    op.create_table(
        "route_segment",
        sa.Column("route_segment_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("route_id", sa.BigInteger(), nullable=False),
        sa.Column("segment_sequence", sa.Integer(), nullable=False),
        sa.Column("encoded_polyline", sa.Text(), nullable=True),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("congestion_level", sa.String(length=20), nullable=True),
        sa.Column("sensory_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("data_availability_status", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["route_option.route_id"],
            name="fk_route_segment_route_id_route_option",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("route_segment_id"),
        sa.UniqueConstraint("route_id", "segment_sequence", name="uq_route_segment_route_id_segment_sequence"),
    )
    op.create_index("ix_route_segment_route_id", "route_segment", ["route_id"])
    op.create_index(
        "ix_route_segment_route_id_segment_sequence",
        "route_segment",
        ["route_id", "segment_sequence"],
    )

    op.create_table(
        "alert",
        sa.Column("alert_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("route_id", sa.BigInteger(), nullable=False),
        sa.Column("route_segment_id", sa.BigInteger(), nullable=True),
        sa.Column("sensor_id", sa.BigInteger(), nullable=True),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["route_option.route_id"],
            name="fk_alert_route_id_route_option",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["route_segment_id"],
            ["route_segment.route_segment_id"],
            name="fk_alert_route_segment_id_route_segment",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sensor_id"],
            ["sensor_location.sensor_id"],
            name="fk_alert_sensor_id_sensor_location",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("alert_id"),
    )
    op.create_index("ix_alert_route_id", "alert", ["route_id"])
    op.create_index("ix_alert_route_id_status_created_at", "alert", ["route_id", "status", "created_at"])
    op.create_index("ix_alert_route_segment_id", "alert", ["route_segment_id"])
    op.create_index("ix_alert_sensor_id", "alert", ["sensor_id"])

    op.create_table(
        "route_refuge_recommendation",
        sa.Column("route_refuge_recommendation_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("route_id", sa.BigInteger(), nullable=False),
        sa.Column("poi_id", sa.BigInteger(), nullable=False),
        sa.Column("recommendation_rank", sa.Integer(), nullable=False),
        sa.Column("distance_from_route_m", sa.Integer(), nullable=True),
        sa.Column("availability_status", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["poi_id"],
            ["point_of_interest.poi_id"],
            name="fk_route_refuge_recommendation_poi_id_point_of_interest",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["route_option.route_id"],
            name="fk_route_refuge_recommendation_route_id_route_option",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("route_refuge_recommendation_id"),
        sa.UniqueConstraint("route_id", "poi_id", name="uq_route_refuge_recommendation_route_id_poi_id"),
    )
    op.create_index(
        "ix_route_refuge_recommendation_poi_id",
        "route_refuge_recommendation",
        ["poi_id"],
    )
    op.create_index(
        "ix_route_refuge_recommendation_route_id",
        "route_refuge_recommendation",
        ["route_id"],
    )

    op.create_table(
        "route_sensor_score",
        sa.Column("route_sensor_score_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("route_segment_id", sa.BigInteger(), nullable=False),
        sa.Column("sensor_id", sa.BigInteger(), nullable=False),
        sa.Column("count_source", sa.String(length=30), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("count_used", sa.Integer(), nullable=True),
        sa.Column("score_contribution", sa.Numeric(6, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["route_segment_id"],
            ["route_segment.route_segment_id"],
            name="fk_route_sensor_score_route_segment_id_route_segment",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sensor_id"],
            ["sensor_location.sensor_id"],
            name="fk_route_sensor_score_sensor_id_sensor_location",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("route_sensor_score_id"),
    )
    op.create_index("ix_route_sensor_score_route_segment_id", "route_sensor_score", ["route_segment_id"])
    op.create_index("ix_route_sensor_score_sensor_id", "route_sensor_score", ["sensor_id"])

    op.create_table(
        "route_transport_stop",
        sa.Column("route_id", sa.BigInteger(), nullable=False),
        sa.Column("stop_id", sa.String(length=100), nullable=False),
        sa.Column("stop_sequence", sa.Integer(), nullable=False),
        sa.Column("stop_role", sa.String(length=30), nullable=True),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["route_option.route_id"],
            name="fk_route_transport_stop_route_id_route_option",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stop_id"],
            ["transport_stop.stop_id"],
            name="fk_route_transport_stop_stop_id_transport_stop",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("route_id", "stop_id", "stop_sequence"),
    )
    op.create_index("ix_route_transport_stop_route_id", "route_transport_stop", ["route_id"])
    op.create_index("ix_route_transport_stop_stop_id", "route_transport_stop", ["stop_id"])

    op.create_table(
        "journey_feedback",
        sa.Column("feedback_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("route_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sensory_rating", sa.SmallInteger(), nullable=False),
        sa.Column("crowd_rating", sa.SmallInteger(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "crowd_rating IS NULL OR crowd_rating BETWEEN 1 AND 5",
            name="ck_journey_feedback_crowd_rating_range",
        ),
        sa.CheckConstraint(
            "sensory_rating BETWEEN 1 AND 5",
            name="ck_journey_feedback_sensory_rating_range",
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["route_option.route_id"],
            name="fk_journey_feedback_route_id_route_option",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("feedback_id"),
    )
    op.create_index("ix_journey_feedback_route_id", "journey_feedback", ["route_id"])
    op.create_index(
        "ix_journey_feedback_route_id_submitted_at",
        "journey_feedback",
        ["route_id", "submitted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_journey_feedback_route_id_submitted_at", table_name="journey_feedback")
    op.drop_index("ix_journey_feedback_route_id", table_name="journey_feedback")
    op.drop_table("journey_feedback")
    op.drop_index("ix_route_transport_stop_stop_id", table_name="route_transport_stop")
    op.drop_index("ix_route_transport_stop_route_id", table_name="route_transport_stop")
    op.drop_table("route_transport_stop")
    op.drop_index("ix_route_sensor_score_sensor_id", table_name="route_sensor_score")
    op.drop_index("ix_route_sensor_score_route_segment_id", table_name="route_sensor_score")
    op.drop_table("route_sensor_score")
    op.drop_index("ix_route_refuge_recommendation_route_id", table_name="route_refuge_recommendation")
    op.drop_index("ix_route_refuge_recommendation_poi_id", table_name="route_refuge_recommendation")
    op.drop_table("route_refuge_recommendation")
    op.drop_index("ix_alert_sensor_id", table_name="alert")
    op.drop_index("ix_alert_route_segment_id", table_name="alert")
    op.drop_index("ix_alert_route_id_status_created_at", table_name="alert")
    op.drop_index("ix_alert_route_id", table_name="alert")
    op.drop_table("alert")
    op.drop_index("ix_route_segment_route_id_segment_sequence", table_name="route_segment")
    op.drop_index("ix_route_segment_route_id", table_name="route_segment")
    op.drop_table("route_segment")
    op.drop_index("ix_route_option_journey_request_id", table_name="route_option")
    op.drop_table("route_option")
    op.drop_index("ix_realtime_pedestrian_count_sensor_id_sensed_at", table_name="realtime_pedestrian_count")
    op.drop_index("ix_realtime_pedestrian_count_sensor_id", table_name="realtime_pedestrian_count")
    op.drop_table("realtime_pedestrian_count")
    op.drop_index("ix_historical_pedestrian_count_sensor_id", table_name="historical_pedestrian_count")
    op.drop_index("ix_historical_pedestrian_count_sensor_date_hour", table_name="historical_pedestrian_count")
    op.drop_table("historical_pedestrian_count")
    op.drop_index("ix_journey_request_preference_id", table_name="journey_request")
    op.drop_table("journey_request")
    op.drop_index("ix_transport_stop_latitude_longitude", table_name="transport_stop")
    op.drop_table("transport_stop")
    op.drop_index("ix_point_of_interest_latitude_longitude", table_name="point_of_interest")
    op.drop_table("point_of_interest")
    op.drop_index("ix_sensor_location_latitude_longitude", table_name="sensor_location")
    op.drop_table("sensor_location")
    op.drop_index("ix_user_preference_session_id", table_name="user_preference")
    op.drop_table("user_preference")
