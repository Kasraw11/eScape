# eScape Database

This folder contains database artefacts for the eScape onboarding iteration.

The current `schema.sql` is aligned to the backend SQLAlchemy models in
`backend/app/models/`. These backend models are recommended as the schema source
of truth because they define what the running FastAPI application reads and
writes.

The schema has been validated against Aiven MySQL using the test database
`escape_ellie_schema_test`.

## Key Files

| File | Purpose |
|---|---|
| `schema.sql` | MySQL schema aligned with backend models |
| `validation_queries.sql` | Basic checks for tables and row counts |
| `data_ingestion_plan.md` | Ingestion and integration notes |
| `PGP_data_management_report.md` | PGP-ready data governance report |
| `schema_review_against_AC` | Schema review against acceptance criteria |
| `raw/pedestrian_counts_sample.csv` | Development-only sample data |

## Aiven Setup

The intended team database name is:

```text
escape_db
```

The tested personal validation database is:

```text
escape_ellie_schema_test
```

Do not rebuild or drop `escape_db` without team agreement.

Backend connection values should be stored locally in:

```text
backend/.env
```

Use `backend/.env.example` as the template. Do not commit real Aiven passwords.

## Ingestion

Run from `backend`:

```powershell
.\.venv\Scripts\python.exe scripts\import_sensor_locations.py
.\.venv\Scripts\python.exe scripts\ingest_realtime_pedestrian_history.py --max-records 6000
.\.venv\Scripts\python.exe scripts\import_sensory_refuges.py
```

Only the realtime pedestrian-count ingestion needs frequent refresh. Sensor
locations and refuge candidates are reference data and only need occasional
refreshes.

## Start with Docker

This option is for local MySQL testing only. Aiven MySQL is the current hosted
database used for integration testing.

From the repository root:

```bash
docker compose up -d mysql
```

MySQL will start with:

- database: from `MYSQL_DATABASE` in `.env`
- user: from `MYSQL_USER` in `.env`
- password: from `MYSQL_PASSWORD` in `.env`
- root password: from `MYSQL_ROOT_PASSWORD` in `.env`
- port: `3306`

The schema in `database/schema.sql` is mounted into MySQL's init directory and runs automatically the first time the container creates its data volume.

## Connect

```bash
mysql -h 127.0.0.1 -P 3306 -u <MYSQL_USER> -p <MYSQL_DATABASE>
```

Replace the placeholders with the values from your local `.env`. Use `MYSQL_PASSWORD` from `.env` when prompted.

## Recreate From Scratch

If you need to reset the local database:

```bash
docker compose down -v
docker compose up -d mysql
```
