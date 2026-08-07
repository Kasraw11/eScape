import httpx
from fastapi import APIRouter, Depends, Query

from app.schemas.crowd import LatestCountsResponse, NearbyRefugesResponse, SensorLocationsResponse
from app.services.city_of_melbourne import (
    CityOfMelbourneClient,
    get_city_client,
    find_nearby_refuges,
    summarise_live_counts,
)

router = APIRouter(prefix="/crowd", tags=["crowd"])


@router.get("/sensor-locations", response_model=SensorLocationsResponse)
async def get_sensor_locations(
    client: CityOfMelbourneClient = Depends(get_city_client),
) -> SensorLocationsResponse:
    try:
        sensors = await client.fetch_sensor_locations()
    except httpx.HTTPError:
        sensors = []
    return SensorLocationsResponse(
        sensors=sensors,
        count=len(sensors),
        source="City of Melbourne Open Data",
    )


@router.get("/latest-counts", response_model=LatestCountsResponse)
async def get_latest_counts(
    client: CityOfMelbourneClient = Depends(get_city_client),
) -> LatestCountsResponse:
    try:
        readings = await client.fetch_latest_pedestrian_counts()
    except httpx.HTTPError:
        readings = []
    return LatestCountsResponse(
        readings=readings,
        count=len(readings),
        summary=summarise_live_counts(readings),
        source="City of Melbourne Open Data",
        data_note=(
            "Past-hour count records may not include every sensor every minute. "
            "Missing readings are treated as unknown, not low crowd."
        ),
    )


@router.get("/refuges/nearby", response_model=NearbyRefugesResponse)
async def get_nearby_refuges(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    limit: int = Query(default=5, ge=1, le=20),
    client: CityOfMelbourneClient = Depends(get_city_client),
) -> NearbyRefugesResponse:
    try:
        refuges = await client.fetch_sensory_refuges()
    except httpx.HTTPError:
        refuges = []

    nearby = find_nearby_refuges(refuges, latitude=latitude, longitude=longitude, limit=limit)
    return NearbyRefugesResponse(
        refuges=nearby,
        count=len(nearby),
        source="City of Melbourne Open Data",
        data_note=(
            "Refuge candidates are filtered from landmarks/POIs. Opening hours and sensory "
            "conditions are unknown unless a later data source provides them."
        ),
    )
