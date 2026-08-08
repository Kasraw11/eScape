from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert import Alert
from app.models.sensory_prediction import SensoryPrediction
from app.repositories.prediction_repository import PredictionRepository
from app.services.prediction_service import PredictionCalculator


logger = logging.getLogger(__name__)


@dataclass
class PredictionJobStats:
    predictions_inserted: int = 0
    predictions_updated: int = 0
    unavailable: int = 0
    alerts_created: int = 0
    alerts_updated: int = 0
    alerts_closed: int = 0
    unchanged: int = 0
    failed: int = 0


def prediction_target(now: datetime, forecast_minutes: int) -> datetime:
    target = now.astimezone(timezone.utc) + timedelta(minutes=forecast_minutes)
    return target.replace(minute=(target.minute // 15) * 15, second=0, microsecond=0)


class PredictionJobService:
    def __init__(
        self,
        db: Session,
        repository: PredictionRepository | None = None,
        calculator: PredictionCalculator | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or PredictionRepository(db)
        self.calculator = calculator or PredictionCalculator()

    def run(self, now: datetime | None = None, forecast_minutes: int | None = None) -> PredictionJobStats:
        generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        horizon = forecast_minutes or settings.prediction_default_horizon_minutes
        target = prediction_target(generated_at, horizon)
        stats = PredictionJobStats()

        for sensor in self.repository.active_sensors():
            sensor_stats = PredictionJobStats()
            try:
                with self.db.begin_nested():
                    calculation = self.calculator.calculate(
                        prediction_for=target,
                        generated_at=generated_at,
                        recent_counts=self.repository.recent_counts(sensor.sensor_id),
                        historical_counts=self.repository.matching_historical_counts(sensor.sensor_id, target),
                        sensor_source=sensor.source,
                    )
                    prediction = self.db.scalar(
                        select(SensoryPrediction).where(
                            SensoryPrediction.sensor_id == sensor.sensor_id,
                            SensoryPrediction.prediction_for == target,
                            SensoryPrediction.model_version == settings.prediction_model_version,
                        )
                    )
                    values = {
                        "predicted_count": calculation.predicted_count,
                        "severity": calculation.severity,
                        "confidence": calculation.confidence,
                        "generated_at": generated_at,
                        "source_freshness": calculation.source_freshness,
                        "data_availability_status": calculation.data_availability_status,
                        "limitation_message": calculation.limitation_message,
                        "source_validated": calculation.source_validated,
                    }
                    if prediction is None:
                        prediction = SensoryPrediction(
                            sensor_id=sensor.sensor_id,
                            prediction_for=target,
                            model_version=settings.prediction_model_version,
                            **values,
                        )
                        self.db.add(prediction)
                        self.db.flush()
                        sensor_stats.predictions_inserted += 1
                    else:
                        materially_changed = any(getattr(prediction, field) != value for field, value in values.items() if field != "generated_at")
                        for field, value in values.items():
                            setattr(prediction, field, value)
                        sensor_stats.predictions_updated += int(materially_changed)
                        sensor_stats.unchanged += int(not materially_changed)
                    if calculation.data_availability_status == "unavailable":
                        sensor_stats.unavailable += 1
                    self._sync_alert(sensor, prediction, generated_at, sensor_stats)
                for field in (
                    "predictions_inserted", "predictions_updated", "unavailable",
                    "alerts_created", "alerts_updated", "alerts_closed", "unchanged",
                ):
                    setattr(stats, field, getattr(stats, field) + getattr(sensor_stats, field))
            except Exception as exc:
                stats.failed += 1
                logger.warning(
                    "Prediction failed for sensor_id=%s error_type=%s",
                    sensor.sensor_id,
                    exc.__class__.__name__,
                )
        return stats

    def _sync_alert(self, sensor, prediction: SensoryPrediction, now: datetime, stats: PredictionJobStats) -> None:
        dedup_key = f"{sensor.sensor_id}:{prediction.prediction_for.isoformat()}:predictive_crowd"
        qualifies = (
            prediction.severity == "High"
            and prediction.confidence in {"Medium", "High"}
            and prediction.data_availability_status == "available"
            and prediction.source_validated
        )
        existing = self.db.scalar(select(Alert).where(Alert.deduplication_key == dedup_key))
        if not qualifies:
            active = self.db.scalars(
                select(Alert).where(
                    Alert.sensor_id == sensor.sensor_id,
                    Alert.alert_type == "predictive_crowd",
                    Alert.status == "active",
                )
            ).all()
            for alert in active:
                alert.status = "closed"
                alert.updated_at = now
                stats.alerts_closed += 1
            return

        message = (
            f"{sensor.location_name or sensor.sensor_name} is predicted to reach High crowd severity "
            f"at {prediction.prediction_for.isoformat()}."
        )
        active_other = self.db.scalars(
            select(Alert).where(
                Alert.sensor_id == sensor.sensor_id,
                Alert.alert_type == "predictive_crowd",
                Alert.status == "active",
                Alert.deduplication_key != dedup_key,
            )
        ).all()
        for alert in active_other:
            alert.status = "superseded"
            alert.updated_at = now
            stats.alerts_closed += 1

        if existing is None:
            self.db.add(Alert(
                route_id=None,
                sensor_id=sensor.sensor_id,
                prediction_id=prediction.prediction_id,
                deduplication_key=dedup_key,
                alert_type="predictive_crowd",
                severity=prediction.severity,
                message=message,
                status="active",
                created_at=now,
                updated_at=now,
                expires_at=prediction.prediction_for + timedelta(minutes=15),
            ))
            stats.alerts_created += 1
            return
        changed = any((existing.severity != prediction.severity, existing.message != message, existing.status != "active"))
        existing.prediction_id = prediction.prediction_id
        existing.severity = prediction.severity
        existing.message = message
        existing.status = "active"
        existing.updated_at = now
        existing.expires_at = prediction.prediction_for + timedelta(minutes=15)
        stats.alerts_updated += int(changed)
        stats.unchanged += int(not changed)
