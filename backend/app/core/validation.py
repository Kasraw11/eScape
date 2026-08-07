from pydantic import BaseModel, Field, field_validator


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class MelbournePlaceInput(BaseModel):
    label: str = Field(min_length=1, max_length=180)
    coordinates: Coordinate | None = None

    @field_validator("label")
    @classmethod
    def normalise_label(cls, value: str) -> str:
        return " ".join(value.strip().split())
