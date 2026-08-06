from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    database_url: str = ""
    google_maps_api_key: str = ""
    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    pedestrian_live_window_seconds: int = 120
    pedestrian_recent_window_seconds: int = 600
    congestion_poll_interval_seconds: int = 90
    melbourne_pedestrian_api_url: str = (
        "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/"
        "pedestrian-counting-system-past-hour-counts-per-minute/records"
    )
    melbourne_pedestrian_api_timeout_seconds: float = 15.0
    melbourne_pedestrian_api_limit: int = 100

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
