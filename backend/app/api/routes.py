import httpx
from fastapi import APIRouter, Depends

from app.schemas.routes import RoutePlanRequest, RoutePlanResponse
from app.services.city_of_melbourne import CityOfMelbourneClient, get_city_client
from app.services.routing_service import plan_routes

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/plan", response_model=RoutePlanResponse)
async def plan_route(
    payload: RoutePlanRequest,
    client: CityOfMelbourneClient = Depends(get_city_client),
) -> RoutePlanResponse:
    try:
        sensor_locations = await client.fetch_sensor_locations()
        live_counts = await client.fetch_latest_pedestrian_counts()
    except httpx.HTTPError:
        sensor_locations = []
        live_counts = []
    return plan_routes(payload, sensor_locations=sensor_locations, live_counts=live_counts)
