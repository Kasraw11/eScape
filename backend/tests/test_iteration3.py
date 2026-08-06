from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.predictions import get_prediction_query_service
from app.api.refuges import get_refuge_search_service
from app.main import app
from app.schemas.predictions import MinimumSeverity
from app.schemas.refuges import RefugeCategory
from app.services.prediction_job_service import PredictionJobService, PredictionJobStats, prediction_target
from app.services.prediction_query_service import PredictionQueryService
from app.services.prediction_service import PredictionCalculator, TimedCount
from app.services.refuge_ingestion_service import (
    LANDMARKS_SOURCE,
    MelbourneRefugeClient,
    MelbourneRefugeDataError,
    RefugeIngestionService,
)
from app.services.refuge_search_service import RefugeSearchService, opening_status


NOW = datetime(2026, 8, 6, 2, 0, tzinfo=timezone.utc)
MELBOURNE_NOON = datetime(2026, 8, 6, 12, 0, tzinfo=timezone(timedelta(hours=10)))


def refuge(refuge_id: int, name: str, latitude: float, category: str = "Park", hours: str | None = None):
    return SimpleNamespace(
        poi_id=refuge_id,
        feature_name=name,
        theme=category,
        address=f"{refuge_id} Test Street, Melbourne",
        latitude=Decimal(str(latitude)),
        longitude=Decimal("144.9631"),
        opening_hours=hours,
        sensory_notes="Potential quiet space.",
        accessibility_notes="Step-free entry not confirmed.",
        source=LANDMARKS_SOURCE,
        source_record_id=f"source-{refuge_id}",
        last_updated_at=NOW,
        is_sensory_refuge=True,
    )


class FakeRefugeRepository:
    def __init__(self, refuges):
        self.refuges = refuges
        self.category_label = None
        self.db = SimpleNamespace(rollback=lambda: None)

    def list_candidates(self, latitude, longitude, radius_m, category_label=None):
        self.category_label = category_label
        return [item for item in self.refuges if not category_label or item.theme == category_label]

    def get(self, refuge_id):
        return next((item for item in self.refuges if item.poi_id == refuge_id), None)


def test_nearby_refuges_are_exactly_distance_ordered() -> None:
    repository = FakeRefugeRepository([
        refuge(2, "Far park", -37.8200),
        refuge(1, "Near park", -37.8138),
    ])
    result = RefugeSearchService(repository).search(-37.8136, 144.9631, 1000, None, MELBOURNE_NOON, 30)
    assert [item.refuge_id for item in result.results] == [1, 2]
    assert result.results[0].estimated_travel_minutes >= 1


def test_refuge_category_filter_is_applied_in_repository_and_response() -> None:
    repository = FakeRefugeRepository([refuge(1, "Park", -37.8138), refuge(2, "Library", -37.8139, "Library")])
    result = RefugeSearchService(repository).search(-37.8136, 144.9631, 1000, RefugeCategory.LIBRARY, NOW, 30)
    assert repository.category_label == "Library"
    assert [item.category for item in result.results] == ["Library"]


@pytest.mark.parametrize(
    ("selected", "expected"),
    [
        (datetime(2026, 8, 3, 10, 0, tzinfo=timezone(timedelta(hours=10))), "open"),
        (datetime(2026, 8, 3, 18, 0, tzinfo=timezone(timedelta(hours=10))), "closed"),
    ],
)
def test_confirmed_hours_open_and_closed(selected: datetime, expected: str) -> None:
    schedule = json.dumps({"monday": [["09:00", "17:00"]]})
    assert opening_status(schedule, selected)[0] == expected


def test_unconfirmed_hours_are_unavailable() -> None:
    assert opening_status(None, MELBOURNE_NOON) == ("hours_unavailable", None)
    assert opening_status("Mon-Fri 9-5", MELBOURNE_NOON)[0] == "hours_unavailable"


def test_no_refuges_recommends_increasing_radius() -> None:
    result = RefugeSearchService(FakeRefugeRepository([])).search(-37.8136, 144.9631, 100, None, NOW, 10)
    assert result.results == []
    assert "increasing the search radius" in result.message


def test_refuge_details_include_source_notes_and_distance() -> None:
    result = RefugeSearchService(FakeRefugeRepository([refuge(8, "City Library", -37.8140, "Library")])).details(
        8, -37.8136, 144.9631, NOW
    )
    assert result is not None
    assert result.name == "City Library"
    assert result.distance_m > 0
    assert result.source_record_id == "source-8"
    assert "quiet" in result.limitation_message.casefold()


@pytest.fixture()
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_refuge_api_validation_and_radius_limits(client: TestClient) -> None:
    assert client.get("/api/refuges?latitude=-91&longitude=144.9").status_code == 422
    assert client.get("/api/refuges?latitude=-37.8&longitude=144.9&radius_m=99").status_code == 422
    assert client.get("/api/refuges?latitude=-37.8&longitude=144.9&radius_m=5001").status_code == 422


def test_refuge_api_returns_search_contract(client: TestClient) -> None:
    service = RefugeSearchService(FakeRefugeRepository([refuge(1, "Near park", -37.8138)]))
    app.dependency_overrides[get_refuge_search_service] = lambda: service
    response = client.get("/api/refuges?latitude=-37.8136&longitude=144.9631&category=park")
    assert response.status_code == 200
    assert response.json()["results"][0]["name"] == "Near park"


def test_refuge_api_unknown_details(client: TestClient) -> None:
    app.dependency_overrides[get_refuge_search_service] = lambda: RefugeSearchService(FakeRefugeRepository([]))
    assert client.get("/api/refuges/999").status_code == 404


def landmark_record(**overrides):
    return {
        "_dataset_kind": "landmarks",
        "theme": "Leisure/Recreation",
        "sub_theme": "Informal Outdoor Facility (Park/Garden/Reserve)",
        "feature_name": "Treasury Gardens",
        "co_ordinates": [-37.8144, 144.9754],
        **overrides,
    }


def test_refuge_import_prevents_duplicate_records() -> None:
    db = MagicMock()
    db.scalar.return_value = None
    stats = RefugeIngestionService(db).ingest([landmark_record(), landmark_record()], NOW)
    assert stats.inserted == 1
    assert stats.skipped == 1
    assert db.add.call_count == 1


def test_refuge_import_skips_uncertain_categories_and_invalid_coordinates() -> None:
    db = MagicMock()
    stats = RefugeIngestionService(db).ingest([
        landmark_record(sub_theme="Major Sports Facility"),
        landmark_record(co_ordinates=[999, 144.9]),
    ], NOW)
    assert stats.skipped == 1
    assert stats.invalid == 1
    db.add.assert_not_called()


def test_refuge_external_service_failure_is_safe() -> None:
    async def handler(request):
        raise httpx.ConnectError("offline", request=request)
    transport = httpx.MockTransport(handler)

    async def call():
        async with httpx.AsyncClient(transport=transport) as http_client:
            await MelbourneRefugeClient().fetch(http_client)

    with pytest.raises(MelbourneRefugeDataError, match="request failed"):
        asyncio.run(call())


def calculate(*, historical, recent, source="City of Melbourne Open Data", now=NOW):
    return PredictionCalculator().calculate(
        prediction_for=now + timedelta(minutes=60),
        generated_at=now,
        recent_counts=recent,
        historical_counts=historical,
        sensor_source=source,
    )


def test_prediction_uses_matched_historical_mean_and_recent_trend() -> None:
    no_trend = calculate(historical=[100] * 8, recent=[TimedCount(120, NOW)])
    with_trend = calculate(
        historical=[100] * 8,
        recent=[TimedCount(120, NOW), TimedCount(100, NOW - timedelta(minutes=10))],
    )
    assert no_trend.historical_baseline == 100
    assert with_trend.trend_adjustment == 50
    assert with_trend.predicted_count > no_trend.predicted_count


@pytest.mark.parametrize(
    ("latest", "expected"),
    [(30, "Low"), (100, "Moderate"), (200, "High")],
)
def test_prediction_severity_thresholds(latest: int, expected: str) -> None:
    result = calculate(historical=[100] * 8, recent=[TimedCount(latest, NOW)])
    assert result.severity == expected


def test_missing_historical_and_current_data_are_unavailable() -> None:
    no_history = calculate(historical=[], recent=[TimedCount(100, NOW)])
    no_current = calculate(historical=[100] * 8, recent=[])
    assert no_history.severity == "Unavailable" and no_history.predicted_count is None
    assert no_current.severity == "Unavailable" and no_current.predicted_count is None


def test_stale_current_data_is_not_presented_as_certain() -> None:
    result = calculate(historical=[100] * 8, recent=[TimedCount(100, NOW - timedelta(hours=1))])
    assert result.source_freshness == "stale"
    assert result.confidence == "Low"
    assert "stale" in result.limitation_message


def test_confidence_uses_sample_size_freshness_and_trend_stability() -> None:
    high = calculate(
        historical=[100] * 8,
        recent=[TimedCount(110, NOW), TimedCount(105, NOW - timedelta(minutes=10))],
    )
    medium = calculate(historical=[100] * 3, recent=[TimedCount(100, NOW)])
    low = calculate(historical=[100], recent=[TimedCount(100, NOW)])
    assert (high.confidence, medium.confidence, low.confidence) == ("High", "Medium", "Low")


def test_unvalidated_source_is_unavailable_and_honest() -> None:
    result = calculate(historical=[100] * 8, recent=[TimedCount(200, NOW)], source="Synthetic fixture")
    assert result.severity == "Unavailable"
    assert result.source_validated is False
    assert "not validated" in result.limitation_message


def test_development_sample_is_not_treated_as_validated_city_data() -> None:
    result = calculate(
        historical=[100] * 8,
        recent=[TimedCount(200, NOW)],
        source="City of Melbourne sample",
    )
    assert result.severity == "Unavailable"
    assert result.source_validated is False


def test_prediction_target_is_a_stable_fifteen_minute_window() -> None:
    target = prediction_target(datetime(2026, 8, 6, 2, 7, tzinfo=timezone.utc), 60)
    assert target == datetime(2026, 8, 6, 3, 0, tzinfo=timezone.utc)


class FakeJobDb:
    def __init__(self, scalar=None, scalar_rows=None):
        self.scalar_value = scalar
        self.scalar_rows = scalar_rows or []
        self.added = []

    def scalar(self, statement):
        return self.scalar_value

    def scalars(self, statement):
        return SimpleNamespace(all=lambda: self.scalar_rows)

    def add(self, value):
        self.added.append(value)


def prediction(severity="High", confidence="High"):
    return SimpleNamespace(
        prediction_id=9,
        prediction_for=NOW + timedelta(hours=1),
        severity=severity,
        confidence=confidence,
        data_availability_status="available",
        source_validated=True,
    )


def sensor():
    return SimpleNamespace(sensor_id=3, sensor_name="Sensor 3", location_name="Bourke Street")


def test_predictive_alert_creation_and_deduplication() -> None:
    db = FakeJobDb()
    service = PredictionJobService(db, repository=MagicMock())
    stats = PredictionJobStats()
    service._sync_alert(sensor(), prediction(), NOW, stats)
    assert stats.alerts_created == 1
    assert len(db.added) == 1
    assert db.added[0].deduplication_key == "3:2026-08-06T03:00:00+00:00:predictive_crowd"

    existing = db.added[0]
    db.scalar_value = existing
    db.added.clear()
    repeat_stats = PredictionJobStats()
    service._sync_alert(sensor(), prediction(), NOW, repeat_stats)
    assert repeat_stats.alerts_created == 0
    assert db.added == []


def test_predictive_alert_is_updated_materially_and_closed_after_downgrade() -> None:
    existing = SimpleNamespace(
        severity="Moderate", message="old", status="active", prediction_id=1,
        expires_at=None, updated_at=None,
    )
    db = FakeJobDb(scalar=existing)
    service = PredictionJobService(db, repository=MagicMock())
    updated = PredictionJobStats()
    service._sync_alert(sensor(), prediction(), NOW, updated)
    assert updated.alerts_updated == 1
    assert existing.severity == "High"

    db.scalar_rows = [existing]
    closed = PredictionJobStats()
    service._sync_alert(sensor(), prediction(severity="Moderate"), NOW, closed)
    assert existing.status == "closed"
    assert closed.alerts_closed == 1


def test_prediction_api_horizon_validation_and_unavailable_database(client: TestClient) -> None:
    assert client.get("/api/predictions?latitude=-37.8&longitude=144.9&forecast_minutes=61").status_code == 422
    response = client.get("/api/predictions?latitude=-37.8&longitude=144.9")
    assert response.status_code == 503
    assert response.json()["detail"] == "Prediction services are temporarily unavailable."


def test_prediction_api_passes_validated_preferences_to_backend(client: TestClient) -> None:
    calls = {}

    class FakeService:
        db = SimpleNamespace(rollback=lambda: None)
        def alerts(self, **kwargs):
            calls.update(kwargs)
            return {"service_available": True, "alerts": [], "preferences_temporary": True}

    app.dependency_overrides[get_prediction_query_service] = lambda: FakeService()
    response = client.get(
        "/api/alerts/predictive?latitude=-37.8&longitude=144.9&enabled=true&minimum_severity=moderate"
        "&maximum_distance_m=1500&route_only=true"
    )
    assert response.status_code == 200
    assert calls["minimum_severity"] == MinimumSeverity.MODERATE
    assert calls["maximum_distance_m"] == 1500
    assert calls["route_only"] is True


def test_prediction_service_failure_rolls_back_safely(client: TestClient) -> None:
    rolled_back = SimpleNamespace(value=False)

    class FakeService:
        db = SimpleNamespace(rollback=lambda: setattr(rolled_back, "value", True))
        def predictions(self, **kwargs):
            raise RuntimeError("database password must remain private")

    app.dependency_overrides[get_prediction_query_service] = lambda: FakeService()
    response = client.get("/api/predictions?latitude=-37.8&longitude=144.9")
    assert response.status_code == 503
    assert "password" not in response.text
    assert rolled_back.value is True
