# eScape

eScape brings route and sensory information together to help users identify calmer Melbourne CBD routes, receive warnings about potential stressors, and locate calmer alternatives.

## Environment

Backend `.env` values:

```env
DATABASE_URL=mysql+pymysql://avnadmin:PASTE_AIVEN_PASSWORD_HERE@escape-mysql-escapedb.l.aivencloud.com:22620/escape_db?ssl_verify_cert=false
GOOGLE_MAPS_API_KEY=PASTE_GOOGLE_MAPS_SERVER_KEY_HERE
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
PEDESTRIAN_LIVE_WINDOW_SECONDS=120
PEDESTRIAN_RECENT_WINDOW_SECONDS=600
CONGESTION_POLL_INTERVAL_SECONDS=90
MELBOURNE_PEDESTRIAN_API_URL=https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/pedestrian-counting-system-past-hour-counts-per-minute/records
MELBOURNE_SENSOR_LOCATIONS_API_URL=https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/pedestrian-counting-system-sensor-locations/records
MELBOURNE_LANDMARKS_API_URL=https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/landmarks-and-places-of-interest-including-schools-theatres-health-services-spor/records
MELBOURNE_ENVIRONMENTAL_ASSETS_API_URL=https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/assets-for-environmental-reporting/records
PREDICTION_MODEL_VERSION=transparent-trend-v1
PREDICTION_DEFAULT_HORIZON_MINUTES=60
```

Frontend `.env` values:

```env
NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY=PASTE_YOUR_BROWSER_KEY_HERE
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_CONGESTION_POLL_INTERVAL_MS=90000
```

Do not commit real Aiven passwords or Google API keys. Keep secrets only in local
`backend/.env` and `frontend/.env.local` files. The committed `.env.example`
files show the required variable names and placeholder values.

For Google Maps, use a browser key for `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY`
and a server/backend key for `GOOGLE_MAPS_API_KEY` if backend Google services are
enabled. Restrict the browser key to local development origins such as
`http://localhost:3000/*` and `http://127.0.0.1:3000/*`, and restrict both keys
to only the APIs the current branch needs.

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

## Iteration 3 sensory refuges

`python scripts/import_sensory_refuges.py` pages through two City of Melbourne Open Data sources and safely upserts candidates into `point_of_interest`:

- **Landmarks and places of interest**: only the explicit `Informal Outdoor Facility (Park/Garden/Reserve)` sub-theme and explicitly named libraries.
- **Assets for environmental reporting**: only `Library Facilities` records.

Generic community assets, sporting facilities, retail places, and other uncertain categories are skipped. Imported records are described as **potential quiet spaces** and never as certified or guaranteed quiet. The import validates coordinates, generates a stable source identifier when one is absent, prevents duplicates, preserves existing data on external failure, and reports inserted, updated, skipped, and invalid totals.

```powershell
cd "E:\FIT 5120\Onboarding\eScape\backend"
.\.venv\Scripts\python.exe scripts\import_sensory_refuges.py
```

`GET /api/refuges` accepts latitude/longitude, a 100–5000 metre radius (default 1000), optional category, selected date-time, and a 1–100 result limit. Exact great-circle distance uses the Haversine formula in the search service; walking time is an explicit approximation of 80 metres per minute. Structured weekly JSON hours are evaluated in `Australia/Melbourne`. Unconfirmed or free-text hours remain `hours_unavailable`.

The `/refuges` page requests browser location only after an explanation/action (or when permission is already granted), supports controlled Melbourne suburb selection and map selection, and keeps cards, compact/expanded maps, filters, and details synchronized. Directions reuse `POST /api/routes/plan`.

## Iteration 3 next-hour predictions

The deterministic `transparent-trend-v1` forecast uses validated City of Melbourne sensor metadata, current counts, and historical hourly counts. Provenance is stored on every current and historical count row; rows without an approved City Open Data source are excluded. The bundled `database/raw/pedestrian_counts_sample.csv` is development-only and is deliberately rejected as validated production data. Production historical imports must come from the official **Pedestrian Counting System - Monthly (counts per hour)** export and retain that source label. For the target time (up to 60 minutes ahead):

1. `baseline` is the mean for the same sensor, Melbourne-local weekday, and hour.
2. `trend` is `(latest - previous) / elapsed_minutes * horizon_minutes`, capped to ±50% of the baseline.
3. `predicted_count` is `round(0.5 * baseline + 0.5 * latest + trend)`, bounded at zero.
4. Severity is Low below `0.80 * baseline`, Moderate below `1.25 * baseline`, and High at or above `1.25 * baseline`.

Confidence is High with at least eight historical samples, a live current reading, two recent readings, and a stable change no larger than 50% of baseline. It is Medium with at least three historical samples and live/recent current data; otherwise Low. Missing current/history, an invalid zero baseline, or an unvalidated source produces `Unavailable`, never Low. Stale data forces Low confidence. Weather, events, and unexpected outages are not modelled.

Run predictions outside browser requests after refreshing counts:

```powershell
cd "E:\FIT 5120\Onboarding\eScape\backend"
.\.venv\Scripts\python.exe -m app.jobs.run_predictions
```

A production scheduler can run ingestion and then predictions every 10–15 minutes. Each sensor runs in a database savepoint, so one partial failure does not erase other valid forecasts. Predictions are unique per sensor, 15-minute target window, and model version. High predictions with Medium/High confidence create or update one active alert under `sensor_id + forecast_window + predictive_crowd`; changed alerts are updated and stale/downgraded alerts are closed or superseded.

`GET /api/predictions` returns nearby validated forecasts. `GET /api/alerts/predictive` applies enabled, minimum-severity, maximum-distance, and route-only preferences in the backend. Predictive alerts are delivered through the shared notification bell and relevant active-trip alerts appear under Plan → Current Trip.
