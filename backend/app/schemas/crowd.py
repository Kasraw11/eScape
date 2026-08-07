from datetime import date
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.crowd import CrowdLevel


class SensorLocation(BaseModel):
    sensor_id: int = Field(gt=0)
    sensor_name: str = Field(min_length=1, max_length=150)
    sensor_description: str | None = Field(default=None, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    status: str = Field(min_length=1, max_length=40)
    location_type: str | None = Field(default=None, max_length=80)
    installation_date: date | None = None
    direction_1: str | None = Field(default=None, max_length=120)
    direction_2: str | None = Field(default=None, max_length=120)


class SensorLocationsResponse(BaseModel):
    sensors: list[SensorLocation]
    count: int
    source: str


class PedestrianCount(BaseModel):
    location_id: int = Field(gt=0)
    sensing_datetime: datetime
    sensing_date: date
    sensing_time: str = Field(min_length=1, max_length=16)
    direction_1: int = Field(ge=0)
    direction_2: int = Field(ge=0)
    total_of_directions: int = Field(ge=0)
    crowd_level: CrowdLevel


class LiveCrowdSummary(BaseModel):
    total_readings: int
    low_count: int
    medium_count: int
    high_count: int


class LatestCountsResponse(BaseModel):
    readings: list[PedestrianCount]
    count: int
    summary: LiveCrowdSummary
    source: str
    data_note: str


class SensoryRefuge(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    theme: str | None = Field(default=None, max_length=100)
    sub_theme: str | None = Field(default=None, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    distance_m: int | None = Field(default=None, ge=0)
    data_note: str


class NearbyRefugesResponse(BaseModel):
    refuges: list[SensoryRefuge]
    count: int
    source: str
    data_note: str
