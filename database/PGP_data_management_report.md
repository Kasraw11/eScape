# eScape Data Management Plan - Onboarding Iteration

## Purpose

This report documents the data sources, database schema, ingestion process, validation evidence, and data governance considerations for the eScape onboarding iteration.

The application aims to help sensory-sensitive commuters compare calmer Melbourne CBD routes and identify potential sensory refuge locations. The data work in this iteration focuses on storing Open Data in Aiven MySQL so the backend can score routes using recent pedestrian sensor readings.

## Current Status

The database work has been tested on Aiven using the personal validation database `escape_ellie_schema_test`.

| Area | Status |
|---|---|
| Backend schema alignment | `database/schema.sql` aligned to backend SQLAlchemy models |
| Aiven MySQL test database | `escape_ellie_schema_test` created and tested |
| Sensor location ingestion | Working |
| Realtime pedestrian count ingestion | Working manually through backend script |
| Sensory refuge candidate ingestion | Working |
| App route scoring persistence | Working on current branch |
| Intended team database | `escape_db` not rebuilt yet; requires team agreement |

## Open Data Sources

| Dataset | Provider | Access Method | Current Use In Application | Refresh Need |
|---|---|---|---|---|
| Pedestrian Counting System - Sensor Locations | City of Melbourne Open Data | API | Populates `sensor_location` with sensor IDs, names, coordinates, status and metadata | Occasional refresh only |
| Pedestrian Counting System - Past Hour Counts Per Minute | City of Melbourne Open Data | API | Populates `realtime_pedestrian_count` with recent timestamped pedestrian readings | Frequent refresh, suggested 5-15 minutes |
| Landmarks and Places of Interest | City of Melbourne Open Data | API | Provides park, garden, reserve and library candidates for `point_of_interest` | Occasional refresh only |
| Assets for Environmental Reporting | City of Melbourne Open Data | API | Provides library facilities for `point_of_interest` | Occasional refresh only |
| Pedestrian Counting System - Monthly Counts Per Hour | City of Melbourne Open Data | CSV/API planned | Future historical baselines and prediction support | Future iteration |

## Data Flow Pipeline

```text
City of Melbourne Open Data APIs
-> backend ingestion scripts
-> validation and transformation in Python services
-> SQLAlchemy database session using DATABASE_URL
-> Aiven MySQL tables
-> backend route/refuge APIs
-> frontend route and refuge views
```

The frontend does not read local CSV files at runtime. Runtime data comes from the backend, and the backend reads from the Aiven MySQL database configured in `backend/.env`.

## Database Storage

The current schema is stored in:

```text
database/schema.sql
```

The schema has been aligned to the backend SQLAlchemy models under:

```text
backend/app/models/
```

The backend models are recommended as the schema source of truth because they define the tables and fields the running FastAPI application reads and writes.

Key tables:

| Table | Purpose |
|---|---|
| `sensor_location` | Pedestrian sensor metadata and coordinates |
| `realtime_pedestrian_count` | Recent timestamped pedestrian readings |
| `historical_pedestrian_count` | Historical pedestrian readings for baseline/prediction support |
| `point_of_interest` | Potential sensory refuge locations |
| `journey_request` | User route request stored by backend |
| `route_option` | Generated route alternatives |
| `route_segment` | Route sections used for scoring |
| `route_sensor_score` | Matched sensor readings and score contribution for route segments |
| `sensory_prediction` | Future prediction records |
| `alert` | Predictive or route-related alert records |
| `user_preference` | User preference settings |
| `journey_feedback` / `refuge_feedback` | Feedback records |

## Ingestion Commands

Run from:

```powershell
cd C:\Projects\eScape\backend
```

Initial or occasional reference-data refresh:

```powershell
.\.venv\Scripts\python.exe scripts\import_sensor_locations.py
.\.venv\Scripts\python.exe scripts\import_sensory_refuges.py
```

Frequent realtime pedestrian-count refresh:

```powershell
.\.venv\Scripts\python.exe scripts\ingest_realtime_pedestrian_history.py --max-records 6000
```

The realtime ingestion script appends new `(sensor_id, sensed_at)` readings and skips duplicates. It does not wipe the table on each run.

## Validation Evidence

Validation database:

```text
escape_ellie_schema_test
```

Observed evidence after schema alignment and ingestion testing:

| Table | Evidence |
|---|---:|
| `sensor_location` | 134 rows |
| `realtime_pedestrian_count` | Recent City of Melbourne readings ingested |
| `point_of_interest` | 43 potential sensory refuge candidates |
| `journey_request` | Populated after route testing |
| `route_option` | Populated after route testing |
| `route_segment` | Populated after route testing |
| `route_sensor_score` | Populated after route testing with `count_source = realtime` |

Example validation SQL:

```sql
USE escape_ellie_schema_test;

SELECT COUNT(*) FROM sensor_location;
SELECT COUNT(*) FROM realtime_pedestrian_count;
SELECT COUNT(*) FROM point_of_interest;

SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT sensor_id) AS sensors_with_data,
  MIN(sensed_at) AS earliest_reading,
  MAX(sensed_at) AS latest_reading
FROM realtime_pedestrian_count;
```

Route scoring validation:

```sql
SELECT
  r.route_id,
  r.sensory_indicator,
  r.total_sensory_score,
  r.data_availability_status,
  r.is_recommended,
  COUNT(rss.route_sensor_score_id) AS matched_sensor_scores
FROM route_option r
LEFT JOIN route_segment rs
  ON rs.route_id = r.route_id
LEFT JOIN route_sensor_score rss
  ON rss.route_segment_id = rs.route_segment_id
GROUP BY
  r.route_id,
  r.sensory_indicator,
  r.total_sensory_score,
  r.data_availability_status,
  r.is_recommended
ORDER BY r.route_id DESC;
```

This confirms whether generated routes are being matched to realtime pedestrian sensor data stored in Aiven.

## Data Quality And Transformation

Validation and transformation performed by ingestion services:

- Coordinates are parsed and checked for valid latitude/longitude ranges.
- Pedestrian counts are checked to prevent negative values.
- Sensor IDs from pedestrian readings are matched to existing `sensor_location` rows.
- Duplicate realtime readings are skipped by checking the sensor and timestamp already stored.
- Refuge candidates are filtered to defensible categories such as libraries, parks, gardens and reserves.
- Refuge records are labelled as potential sensory refuges, not guaranteed quiet spaces.

## Refresh And Scheduling Plan

Current iteration:

- Sensor locations and refuge candidates are refreshed manually when needed.
- Realtime pedestrian counts are refreshed manually using the ingestion script.

Recommended next step:

- Add a scheduler or cloud cron job to run realtime pedestrian ingestion every 5-15 minutes.
- Keep sensor/refuge reference-data ingestion as occasional or daily jobs.

## Legal, Privacy And Ethics

The current system uses public Open Data from the City of Melbourne. The pedestrian datasets are aggregated sensor counts and do not contain personal identifiers.

Ethical boundaries:

- Do not claim that refuge candidates are guaranteed quiet in real time.
- Do not generalise pedestrian sensor results outside the sensor coverage area.
- Clearly show unavailable or partial data when a route is outside sensor coverage.
- Do not merge pedestrian sensor data with personal identity data.
- Attribute Open Data sources in project documentation.

## Security Considerations

Secrets must not be committed to GitHub.

Local-only secret files:

```text
backend/.env
frontend/.env.local
```

Committed example files use placeholders only:

```text
backend/.env.example
frontend/.env.example
database/.env.example
```

Security risks and mitigations:

| Risk | Mitigation |
|---|---|
| Aiven password leakage | Keep in `.env` only; rotate if exposed |
| Google API key misuse | Restrict key by website/API and do not commit real keys |
| Accidental overwrite of team DB | Test in `escape_ellie_schema_test`; rebuild `escape_db` only after team agreement |
| Stale realtime data | Add scheduled ingestion in future |

## Known Limitations

- Realtime data is only as fresh as the latest ingestion run.
- Noise and brightness are not currently supported by validated Open Data sources.
- Refuge quietness is inferred from category, not measured live.
- Operating hours may be unavailable where the source dataset does not provide structured hours.
- OpenStreetMap/OSRM route integration still needs validation against the Aiven scoring flow once the team branch is stable.
- Historical monthly pedestrian ingestion is not fully implemented for production baselines.

## Next Team Decisions

1. Confirm that backend SQLAlchemy models are the schema source of truth.
2. Decide when to rebuild or update `escape_db` from the aligned `schema.sql`.
3. Decide whether teammates will temporarily test against `escape_ellie_schema_test`.
4. Integrate and validate the OSM/OSRM route branch with Aiven-backed sensor scoring.
5. Decide which acceptance criteria are MVP versus future iteration, especially noise, brightness, prediction alerts and live refuge quietness.

## PGP Evidence To Upload

Recommended evidence for the Project Governance Portfolio:

- This Data Management Plan report.
- Updated ERD/logical model.
- Data dictionary.
- `database/schema.sql`.
- `database/validation_queries.sql`.
- Screenshots of Aiven table list and row counts.
- Screenshot of route scoring validation showing `route_sensor_score.count_source = realtime`.
- GitHub branch link: `database/ellie-review`.
- Commit screenshots or GitHub comparison link.
- Notes on known limitations and future scheduling.
