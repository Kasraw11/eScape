import httpx
from fastapi import APIRouter, Depends

from app.schemas.routes import RoutePlanRequest, RoutePlanResponse
from app.services.city_of_melbourne import CityOfMelbourneClient, get_city_client
from app.services.google_routes import GoogleRoutesClient, get_google_routes_client
from app.services.routing_service import plan_routes

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/plan", response_model=RoutePlanResponse)
async def plan_route(
    payload: RoutePlanRequest,
    client: CityOfMelbourneClient = Depends(get_city_client),
    google_routes_client: GoogleRoutesClient = Depends(get_google_routes_client),
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
        google_route_options = await google_routes_client.compute_walking_routes(payload)
    except httpx.HTTPError:
        google_route_options = []

    return plan_routes(
        payload,
        sensor_locations=sensor_locations,
        live_counts=live_counts,
        route_options=google_route_options,
        count_source_label=count_source_label,
    )
