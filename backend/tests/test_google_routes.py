import httpx
import pytest
import respx

from app.schemas.routes import RoutePlanRequest
from app.services.google_routes import GoogleRoutesClient, parse_google_routes


def test_parse_google_routes_converts_geojson_to_route_segments() -> None:
    routes = parse_google_routes(
        {
            "routes": [
                {
                    "distanceMeters": 860,
                    "duration": "620s",
                    "routeLabels": ["DEFAULT_ROUTE"],
                    "polyline": {
                        "geoJsonLinestring": {
                            "coordinates": [
                                [144.9671, -37.8183],
                                [144.9659, -37.8142],
                                [144.9652, -37.8098],
                            ]
                        }
                    },
                }
            ]
        }
    )

    assert len(routes) == 1
    assert routes[0].route_id == "google-1"
    assert routes[0].estimated_duration_min == 10
    assert len(routes[0].segments) == 2
    assert routes[0].segments[0].start.latitude == -37.8183


@pytest.mark.anyio
async def test_google_routes_client_returns_empty_without_key() -> None:
    client = GoogleRoutesClient(api_key="", base_url="https://routes.googleapis.com", timeout_seconds=5)

    routes = await client.compute_walking_routes(
        RoutePlanRequest(
            origin={"label": "Flinders Street Station"},
            destination={"label": "State Library Victoria"},
        )
    )

    assert routes == []


@pytest.mark.anyio
async def test_google_routes_client_calls_compute_routes_with_key() -> None:
    client = GoogleRoutesClient(
        api_key="test-key",
        base_url="https://routes.googleapis.com",
        timeout_seconds=5,
    )

    with respx.mock:
        route = respx.post("https://routes.googleapis.com/directions/v2:computeRoutes").mock(
            return_value=httpx.Response(
                200,
                json={
                    "routes": [
                        {
                            "distanceMeters": 860,
                            "duration": "620s",
                            "routeLabels": ["DEFAULT_ROUTE"],
                            "polyline": {
                                "geoJsonLinestring": {
                                    "coordinates": [
                                        [144.9671, -37.8183],
                                        [144.9652, -37.8098],
                                    ]
                                }
                            },
                        }
                    ]
                },
            )
        )

        routes = await client.compute_walking_routes(
            RoutePlanRequest(
                origin={"label": "Flinders Street Station"},
                destination={"label": "State Library Victoria"},
            )
        )

    assert route.called
    assert len(routes) == 1
