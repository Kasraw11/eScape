import httpx
import pytest
import respx

from app.schemas.routes import RoutePlanRequest
from app.services.openrouteservice_client import (
    OpenRouteServiceClient,
    parse_openrouteservice_routes,
)


def test_parse_openrouteservice_routes_converts_geojson_to_route_segments() -> None:
    routes = parse_openrouteservice_routes(
        {
            "features": [
                {
                    "geometry": {
                        "coordinates": [
                            [144.9671, -37.8183],
                            [144.9659, -37.8142],
                            [144.9652, -37.8098],
                        ]
                    },
                    "properties": {"summary": {"distance": 860, "duration": 620}},
                }
            ]
        }
    )

    assert len(routes) == 1
    assert routes[0].route_id == "ors-1"
    assert routes[0].estimated_duration_min == 10
    assert len(routes[0].segments) == 2
    assert routes[0].segments[0].start.latitude == -37.8183


@pytest.mark.anyio
async def test_openrouteservice_client_returns_empty_without_key() -> None:
    client = OpenRouteServiceClient(api_key="", base_url="https://api.openrouteservice.org", timeout_seconds=5)

    routes = await client.compute_walking_routes(
        RoutePlanRequest(
            origin={"label": "Flinders Street Station"},
            destination={"label": "State Library Victoria"},
        )
    )

    assert routes == []


@pytest.mark.anyio
async def test_openrouteservice_client_calls_directions_with_key() -> None:
    client = OpenRouteServiceClient(
        api_key="test-key",
        base_url="https://api.openrouteservice.org",
        timeout_seconds=5,
    )

    with respx.mock:
        route = respx.post("https://api.openrouteservice.org/v2/directions/foot-walking/geojson").mock(
            return_value=httpx.Response(
                200,
                json={"features": []},
            )
        )

        routes = await client.compute_walking_routes(
            RoutePlanRequest(
                origin={"label": "Flinders Street Station"},
                destination={"label": "State Library Victoria"},
            )
        )

    assert route.called
    assert len(routes) == 0
