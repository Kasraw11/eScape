from __future__ import annotations

import json
from pathlib import Path

from app.database import SessionLocal
from app.models.transport_stop import TransportStop


# Melbourne CBD boundary used by eScape.
MELBOURNE_CBD_LATITUDE_RANGE = (-37.8255, -37.8050)
MELBOURNE_CBD_LONGITUDE_RANGE = (144.9440, 144.9765)


# Only transport modes required for the MVP.
SUPPORTED_MODES = {
    "METRO TRAM": "tram",
    "METRO TRAIN": "train",
    "METRO BUS": "bus",
}


# Location of the downloaded Transport Victoria GeoJSON file.
DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "transport"
    / "raw"
    / "public_transport_stops.geojson"
)


def is_in_melbourne_cbd(latitude: float, longitude: float) -> bool:
    """
    Returns True when a transport stop is inside
    the Melbourne CBD area supported by eScape.
    """

    return (
        MELBOURNE_CBD_LATITUDE_RANGE[0]
        <= latitude
        <= MELBOURNE_CBD_LATITUDE_RANGE[1]
        and MELBOURNE_CBD_LONGITUDE_RANGE[0]
        <= longitude
        <= MELBOURNE_CBD_LONGITUDE_RANGE[1]
    )


def import_transport_stops() -> None:
    """
    Imports Melbourne CBD tram, train and bus stops
    from the Transport Victoria GeoJSON dataset.
    """

    if SessionLocal is None:
        raise RuntimeError("Database is not configured")

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Transport stop dataset was not found at: {DATA_FILE}"
        )

    print(f"Reading transport data from:\n{DATA_FILE}\n")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    features = data.get("features", [])

    print(f"Total records in source file: {len(features)}")

    db = SessionLocal()

    inserted_count = 0
    updated_count = 0
    skipped_outside_cbd = 0
    skipped_mode = 0
    skipped_invalid = 0

    try:
        for feature in features:
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}

            stop_id = properties.get("STOP_ID")
            stop_name = properties.get("STOP_NAME")
            source_mode = properties.get("MODE")

            # We only want metropolitan tram, train and bus stops.
            if source_mode not in SUPPORTED_MODES:
                skipped_mode += 1
                continue

            if geometry.get("type") != "Point":
                skipped_invalid += 1
                continue

            coordinates = geometry.get("coordinates")

            if not coordinates or len(coordinates) < 2:
                skipped_invalid += 1
                continue

            # GeoJSON coordinates are:
            # [longitude, latitude]
            longitude = float(coordinates[0])
            latitude = float(coordinates[1])

            if not is_in_melbourne_cbd(latitude, longitude):
                skipped_outside_cbd += 1
                continue

            if stop_id is None or not stop_name:
                skipped_invalid += 1
                continue

            stop_id = str(stop_id)

            mode = SUPPORTED_MODES[source_mode]

            # Makes the importer safe to run multiple times.
            existing_stop = db.get(TransportStop, stop_id)

            if existing_stop is not None:
                existing_stop.mode = mode
                existing_stop.stop_name = str(stop_name)
                existing_stop.latitude = latitude
                existing_stop.longitude = longitude

                updated_count += 1

            else:
                transport_stop = TransportStop(
                    stop_id=stop_id,
                    mode=mode,
                    stop_name=str(stop_name),
                    latitude=latitude,
                    longitude=longitude,
                )

                db.add(transport_stop)

                inserted_count += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    print("\nTransport stop import complete.")
    print("--------------------------------")
    print(f"Inserted:            {inserted_count}")
    print(f"Updated:             {updated_count}")
    print(f"Outside CBD:         {skipped_outside_cbd}")
    print(f"Unsupported mode:    {skipped_mode}")
    print(f"Invalid records:     {skipped_invalid}")
    print(f"CBD stops processed: {inserted_count + updated_count}")


if __name__ == "__main__":
    import_transport_stops()