from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SensoryPrediction(Base):
    __tablename__ = "sensory_prediction"
    __table_args__ = (
        UniqueConstraint(
            "sensor_id",
            "prediction_for",
            "model_version",
            name="uq_sensory_prediction_sensor_target_model",
        ),
        Index("ix_sensory_prediction_prediction_for", "prediction_for"),
        Index("ix_sensory_prediction_sensor_id", "sensor_id"),
    )

    prediction_id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sensor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sensor_location.sensor_id", ondelete="RESTRICT"),
        nullable=False,
    )
    prediction_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_count: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_freshness: Mapped[str] = mapped_column(String(20), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    data_availability_status: Mapped[str] = mapped_column(String(30), nullable=False)
    limitation_message: Mapped[str | None] = mapped_column(Text)
    source_validated: Mapped[bool] = mapped_column(nullable=False)

    sensor_location: Mapped["SensorLocation"] = relationship(
        "SensorLocation",
        back_populates="sensory_predictions",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="sensory_prediction",
    )
