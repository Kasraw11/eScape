from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.sensor_location import SensorLocation
from app.models.sensory_prediction import SensoryPrediction
from app.schemas.predictions import (
    PREDICTION_UNAVAILABLE_MESSAGE,
    MinimumSeverity,
    PredictionResponse,
    PredictionSearchResponse,
    PredictiveAlertResponse,
    PredictiveAlertSearchResponse,
)
from app.services.sensor_matching_service import haversine_meters


SEVERITY_RANK = {"Unavailable": 0, "Low": 1, "Moderate": 2, "High": 3}


class PredictionQueryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def predictions(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: int,
        forecast_minutes: int,
        minimum_severity: MinimumSeverity,
        now: datetime | None = None,
    ) -> PredictionSearchResponse:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        rows = self.db.execute(
            select(SensoryPrediction, SensorLocation)
            .join(SensorLocation, SensorLocation.sensor_id == SensoryPrediction.sensor_id)
            .where(
                SensoryPrediction.prediction_for >= current - timedelta(minutes=5),
                SensoryPrediction.prediction_for <= current + timedelta(minutes=forecast_minutes),
                SensoryPrediction.source_validated.is_(True),
                SensoryPrediction.data_availability_status == "available",
            )
        ).all()
        minimum_rank = SEVERITY_RANK[minimum_severity.value.title()]
        latest_by_sensor: dict[int, tuple[SensoryPrediction, SensorLocation, int]] = {}
        for prediction, sensor in rows:
            distance = round(haversine_meters((latitude, longitude), (float(sensor.latitude), float(sensor.longitude))))
            if distance > radius_m or SEVERITY_RANK.get(prediction.severity, 0) < minimum_rank:
                continue
            existing = latest_by_sensor.get(sensor.sensor_id)
            if existing is None or prediction.generated_at > existing[0].generated_at:
                latest_by_sensor[sensor.sensor_id] = (prediction, sensor, distance)

        predictions = [self._prediction_response(*item) for item in latest_by_sensor.values()]
        predictions.sort(key=lambda item: (-SEVERITY_RANK[item.severity], item.distance_m, item.prediction_for))
        return PredictionSearchResponse(
            service_available=bool(predictions),
            predictions=predictions,
            forecast_minutes=forecast_minutes,
            generated_at=max((item.generated_at for item in predictions), default=None),
            message=None if predictions else PREDICTION_UNAVAILABLE_MESSAGE,
        )

    def alerts(
        self,
        *,
        latitude: float,
        longitude: float,
        enabled: bool,
        minimum_severity: MinimumSeverity,
        maximum_distance_m: int,
        route_only: bool,
        now: datetime | None = None,
    ) -> PredictiveAlertSearchResponse:
        if not enabled:
            return PredictiveAlertSearchResponse(
                service_available=True,
                alerts=[],
                message="Predictive alerts are disabled by the current temporary preference.",
            )
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        statement = (
            select(Alert, SensoryPrediction, SensorLocation)
            .join(SensoryPrediction, SensoryPrediction.prediction_id == Alert.prediction_id)
            .join(SensorLocation, SensorLocation.sensor_id == Alert.sensor_id)
            .where(
                Alert.alert_type == "predictive_crowd",
                Alert.status == "active",
                or_(Alert.expires_at.is_(None), Alert.expires_at > current),
                SensoryPrediction.source_validated.is_(True),
            )
        )
        if route_only:
            statement = statement.where(Alert.route_id.is_not(None))
        minimum_rank = SEVERITY_RANK[minimum_severity.value.title()]
        by_key: dict[str, PredictiveAlertResponse] = {}
        for alert, prediction, sensor in self.db.execute(statement).all():
            if SEVERITY_RANK.get(alert.severity, 0) < minimum_rank:
                continue
            distance = round(haversine_meters((latitude, longitude), (float(sensor.latitude), float(sensor.longitude))))
            if distance > maximum_distance_m:
                continue
            key = alert.deduplication_key or str(alert.alert_id)
            response = PredictiveAlertResponse(
                alert_id=alert.alert_id,
                deduplication_key=key,
                prediction_id=prediction.prediction_id,
                sensor_id=sensor.sensor_id,
                location_name=sensor.location_name or sensor.sensor_name,
                latitude=float(sensor.latitude),
                longitude=float(sensor.longitude),
                distance_m=distance,
                predicted_time=prediction.prediction_for,
                severity=prediction.severity,
                confidence=prediction.confidence,
                message=alert.message,
                suggested_action="View the area on the map or review route alternatives.",
                route_impact="Selected route affected" if alert.route_id else "Nearby area; route impact not confirmed",
                status=alert.status,
                updated_at=alert.updated_at or alert.created_at,
                data_freshness=prediction.source_freshness,
                source_validated=prediction.source_validated,
            )
            previous = by_key.get(key)
            if previous is None or response.updated_at > previous.updated_at:
                by_key[key] = response
        alerts = sorted(by_key.values(), key=lambda item: (item.predicted_time, -SEVERITY_RANK[item.severity], item.distance_m))
        return PredictiveAlertSearchResponse(service_available=True, alerts=alerts)

    @staticmethod
    def _prediction_response(prediction: SensoryPrediction, sensor: SensorLocation, distance: int) -> PredictionResponse:
        return PredictionResponse(
            prediction_id=prediction.prediction_id,
            sensor_id=sensor.sensor_id,
            location_name=sensor.location_name or sensor.sensor_name,
            latitude=float(sensor.latitude),
            longitude=float(sensor.longitude),
            distance_m=distance,
            prediction_for=prediction.prediction_for,
            predicted_count=prediction.predicted_count,
            severity=prediction.severity,
            confidence=prediction.confidence,
            generated_at=prediction.generated_at,
            source_data_freshness=prediction.source_freshness,
            data_availability_status=prediction.data_availability_status,
            limitation_message=prediction.limitation_message,
            data_source="City of Melbourne Pedestrian Counting System",
            source_validated=prediction.source_validated,
        )
