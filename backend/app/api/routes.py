import httpx
from fastapi import APIRouter, Depends

from app.schemas.routes import RoutePlanRequest, RoutePlanResponse
from app.services.city_of_melbourne import CityOfMelbourneClient, get_city_client
from app.services.openrouteservice_client import (
    OpenRouteServiceClient,
    OsmRouteServiceClient,
    get_openrouteservice_client,
    get_osm_route_client,
)
from app.services.routing_service import plan_routes

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/plan", response_model=RoutePlanResponse)
async def plan_route(
    payload: RoutePlanRequest,
    client: CityOfMelbourneClient = Depends(get_city_client),
    routing_client: OpenRouteServiceClient = Depends(get_openrouteservice_client),
    osrm_client: OsmRouteServiceClient = Depends(get_osm_route_client),
) -> RoutePlanResponse:
    try:
        sensor_locations = await client.fetch_sensor_locations()
    except httpx.HTTPError:
        sensor_locations = []

    try:
        live_counts = await client.fetch_latest_pedestrian_counts()
    except httpx.HTTPError:
        live_counts = []

    count_source_label = "City of Melbourne live past-hour pedestrian counts"
    if not live_counts:
        try:
            live_counts = await client.fetch_recent_hourly_counts_fallback()
            if live_counts:
                count_source_label = "City of Melbourne recent historical hourly pedestrian counts"
        except httpx.HTTPError:
            live_counts = []

    try:
        route_options = await routing_client.compute_walking_routes(payload)
    except httpx.HTTPError:
        route_options = []

    route_geometry_source = "openrouteservice" if route_options else "demo"
    if not route_options:
        try:
            route_options = await osrm_client.compute_walking_routes(payload)
            if route_options:
                route_geometry_source = "osrm"
        except httpx.HTTPError:
            route_options = []

    return plan_routes(
        payload,
        sensor_locations=sensor_locations,
        live_counts=live_counts,
        route_options=route_options,
        count_source_label=count_source_label,
        route_geometry_source=route_geometry_source,
    )
