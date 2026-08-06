# eScape

eScape brings route and sensory information together to help users identify calmer Melbourne CBD routes, receive warnings about potential stressors, and locate calmer alternatives.

## Environment

Backend `.env` values:

```env
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@localhost:5432/escape_db
GOOGLE_MAPS_API_KEY=
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
PEDESTRIAN_LIVE_WINDOW_SECONDS=120
PEDESTRIAN_RECENT_WINDOW_SECONDS=600
CONGESTION_POLL_INTERVAL_SECONDS=90
MELBOURNE_PEDESTRIAN_API_URL=https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/pedestrian-counting-system-past-hour-counts-per-minute/records
```

Frontend `.env` values:

```env
NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY=
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_CONGESTION_POLL_INTERVAL_MS=90000
```

## Backend

```powershell
cd "E:\FIT 5120\Onboarding\eScape\backend"
py -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend

```powershell
cd "E:\FIT 5120\Onboarding\eScape\frontend"
npm install
npm run dev
```

Open `http://localhost:3000`.

## Iteration 2 congestion model

The backend is the source of truth for the crowd-preference scale. Levels 1-5 map to accepted normalised congestion scores of `0.55`, `0.80`, `1.00`, `1.25`, and `1.50` respectively.

For each covered segment:

1. Each current sensor reading is divided by that sensor's historical mean.
2. When no valid historical mean exists, the documented fallback baseline is 300 pedestrians.
3. Matched sensor ratios are averaged for the segment.
4. Route scores are segment-distance-weighted means.
5. Scores below `1.25` are Low and scores at or above `1.25` are High.

The baseline is intentionally a coarse per-sensor mean; it is not presented as a precise weekday or seasonal forecast. Missing coverage remains Unavailable.

Freshness is classified centrally:

- `live`: at most 2 minutes old
- `recent`: more than 2 and at most 10 minutes old
- `stale`: more than 10 minutes old
- `historical`: explicitly selected historical data
- `unavailable`: no suitable reading

The frontend polls `GET /api/routes/{route_id}/congestion` every 90 seconds only while a persisted route is selected, the page is visible, the browser is online, and no request is already running. Temporary failures retain the last valid state.

## Realtime pedestrian ingestion

The ingestion command reads the City of Melbourne **Pedestrian Counting System - Past Hour (counts per minute)** API, validates non-negative timezone-aware readings, maps them to existing `sensor_location` records, and inserts or updates `realtime_pedestrian_count` without deleting previous valid data:

```powershell
cd "E:\FIT 5120\Onboarding\eScape\backend"
.\.venv\Scripts\python.exe scripts\ingest_realtime_pedestrian_counts.py
```

In production, invoke this same idempotent command from the platform scheduler approximately every 15 minutes, matching the source feed's published update cadence. It is separate from FastAPI request handling and does not require a permanently running worker.

## Testing

```powershell
cd "E:\FIT 5120\Onboarding\eScape\backend"
.\.venv\Scripts\python.exe -m pytest -v

cd "E:\FIT 5120\Onboarding\eScape\frontend"
npm run lint
npm test
npm run build
```
