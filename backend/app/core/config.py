from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "eScape API"
    app_version: str = "0.1.0"
    app_debug: bool = Field(default=True, alias="APP_DEBUG")

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_database: str = Field(default="escape_db", alias="MYSQL_DATABASE")
    mysql_user: str = Field(default="escape_user", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")

    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="BACKEND_CORS_ORIGINS",
    )
    city_of_melbourne_base_url: str = Field(
        default="https://data.melbourne.vic.gov.au",
        alias="CITY_OF_MELBOURNE_BASE_URL",
    )
    external_api_timeout_seconds: float = Field(
        default=10.0,
        alias="EXTERNAL_API_TIMEOUT_SECONDS",
    )
    google_maps_api_key: str = Field(default="", alias="GOOGLE_MAPS_API_KEY")
    google_routes_base_url: str = Field(
        default="https://routes.googleapis.com",
        alias="GOOGLE_ROUTES_BASE_URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
