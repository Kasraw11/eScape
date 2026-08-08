# eScape PostgreSQL Database Schema

## Purpose

This schema describes the PostgreSQL data model for eScape, a sensory-aware urban navigation application for Melbourne CBD. It supports route alternatives, sensory scoring, pedestrian congestion monitoring, alerts, refuge recommendations, public-transport stop context, and journey feedback.

The schema is implemented through SQLAlchemy models and Alembic migrations. Migration `0003` adds the Iteration 3 refuge metadata, persisted predictions, and route-optional predictive-alert links described below.

## Iteration 3 additions

`point_of_interest` additionally stores `source_record_id`, `accessibility_notes`, and `sensory_notes`. `(source, source_record_id)` is unique so repeatable City of Melbourne imports update rather than duplicate a place.

`sensory_prediction` persists one deterministic result per `(sensor_id, prediction_for, model_version)`: predicted count, severity, confidence, generation time, source freshness, availability, limitation text, and City-source validation metadata. It references `sensor_location` with restricted deletion.

`alert.route_id` is nullable for area-based predictive alerts. Predictive alerts may reference `sensory_prediction` through nullable `prediction_id`; `deduplication_key` identifies a stable sensor/forecast-window condition and `updated_at` records material refreshes. Existing route and congestion alerts remain supported.

## PostgreSQL Design Decisions

- Table and column names use lowercase `snake_case`.
- Primary keys use `BIGINT` identity columns for application-owned records, except `transport_stop.stop_id`, which is a source-provided `VARCHAR(100)` identifier.
- Session tracking uses `UUID` without storing account or authentication data.
- Time-aware records use `TIMESTAMPTZ` so route requests, alerts, counts, and feedback retain timezone context.
- Latitude and longitude use `NUMERIC(9,6)` with range checks.
- Route geometry is stored as encoded polylines in `TEXT` fields at route and segment levels.
- Pedestrian counts are split into historical and real-time tables because their grain, freshness, and query patterns differ.
- `route_option` intentionally does not duplicate origin, destination, or `preference_id`; it derives those through `journey_request`.
- `route_sensor_score` uses its own identity primary key rather than a composite `route_id` and `sensor_id` key, because scoring belongs to a route segment and may involve different count sources or observation times.
- Shared reference data such as sensors, points of interest, and transport stops should use `RESTRICT` or `NO ACTION` deletion behavior.

## Tables

### user_preference

Stores anonymous session-level navigation preferences.

| Column | Type | Constraints |
| --- | --- | --- |
| preference_id | BIGINT | Primary key, identity |
| session_id | UUID | Unique, not null |
| preferred_crowd_threshold | SMALLINT | Not null, check between 1 and 5 |
| notifications_enabled | BOOLEAN | Not null, default true |
| search_radius_m | INTEGER | Not null, check greater than 0 |
| created_at | TIMESTAMPTZ | Not null |
| updated_at | TIMESTAMPTZ | Not null |

Primary key:
- `preference_id`

Unique constraints:
- `session_id`

Check constraints:
- `preferred_crowd_threshold BETWEEN 1 AND 5`
- `search_radius_m > 0`

### journey_request

Represents one user route search from an origin to a destination. A journey request captures the coordinates and mode for the search, then groups all returned route alternatives under that one request. This avoids duplicating origin, destination, travel mode, and preference context across each route option.

| Column | Type | Constraints |
| --- | --- | --- |
| journey_request_id | BIGINT | Primary key, identity |
| preference_id | BIGINT | Foreign key to `user_preference.preference_id` |
| origin_latitude | NUMERIC(9,6) | Not null, check between -90 and 90 |
| origin_longitude | NUMERIC(9,6) | Not null, check between -180 and 180 |
| destination_latitude | NUMERIC(9,6) | Not null, check between -90 and 90 |
| destination_longitude | NUMERIC(9,6) | Not null, check between -180 and 180 |
| travel_mode | VARCHAR(30) | Not null |
| requested_at | TIMESTAMPTZ | Not null |

Primary key:
- `journey_request_id`

Foreign keys:
- `preference_id` references `user_preference.preference_id`

Check constraints:
- `origin_latitude BETWEEN -90 AND 90`
- `origin_longitude BETWEEN -180 AND 180`
- `destination_latitude BETWEEN -90 AND 90`
- `destination_longitude BETWEEN -180 AND 180`

### route_option

Stores each route alternative returned for a journey request. Multiple route options may exist for the same journey request, including the recommended route and non-recommended alternatives.

| Column | Type | Constraints |
| --- | --- | --- |
| route_id | BIGINT | Primary key, identity |
| journey_request_id | BIGINT | Foreign key to `journey_request.journey_request_id` |
| google_route_id | VARCHAR(255) | Nullable |
| encoded_polyline | TEXT | Nullable |
| estimated_travel_minutes | INTEGER | Not null |
| sensory_indicator | VARCHAR(20) | Not null |
| total_sensory_score | NUMERIC(6,2) | Nullable |
| data_availability_status | VARCHAR(30) | Not null |
| is_recommended | BOOLEAN | Not null, default false |
| created_at | TIMESTAMPTZ | Not null |
| expires_at | TIMESTAMPTZ | Nullable |

Primary key:
- `route_id`

Foreign keys:
- `journey_request_id` references `journey_request.journey_request_id`

Design note:
- `origin`, `destination`, and `preference_id` are intentionally not repeated in `route_option`.

### route_segment

Breaks a route option into ordered segments so congestion and sensory scoring can be attached to the specific part of a route where it applies. This supports segment-level warnings and avoids treating a route as uniformly calm or congested.

| Column | Type | Constraints |
| --- | --- | --- |
| route_segment_id | BIGINT | Primary key, identity |
| route_id | BIGINT | Foreign key to `route_option.route_id` |
| segment_sequence | INTEGER | Not null |
| encoded_polyline | TEXT | Nullable |
| distance_m | INTEGER | Nullable |
| duration_seconds | INTEGER | Nullable |
| congestion_level | VARCHAR(20) | Nullable |
| sensory_score | NUMERIC(6,2) | Nullable |
| data_availability_status | VARCHAR(30) | Nullable |

Primary key:
- `route_segment_id`

Foreign keys:
- `route_id` references `route_option.route_id`

Unique constraints:
- `route_id`, `segment_sequence`

### sensor_location

Stores pedestrian sensor metadata and location details.

| Column | Type | Constraints |
| --- | --- | --- |
| sensor_id | BIGINT | Primary key, identity |
| sensor_name | VARCHAR(255) | Not null |
| description | TEXT | Nullable |
| location_name | VARCHAR(255) | Nullable |
| location_type | VARCHAR(50) | Nullable |
| latitude | NUMERIC(9,6) | Not null, check between -90 and 90 |
| longitude | NUMERIC(9,6) | Not null, check between -180 and 180 |
| installation_date | DATE | Nullable |
| status | VARCHAR(30) | Not null |
| direction_1 | VARCHAR(100) | Nullable |
| direction_2 | VARCHAR(100) | Nullable |
| source | VARCHAR(100) | Nullable |
| last_updated_at | TIMESTAMPTZ | Nullable |

Primary key:
- `sensor_id`

Check constraints:
- `latitude BETWEEN -90 AND 90`
- `longitude BETWEEN -180 AND 180`

### historical_pedestrian_count

Stores hourly historical counts by sensor.

| Column | Type | Constraints |
| --- | --- | --- |
| historical_count_id | BIGINT | Primary key, identity |
| sensor_id | BIGINT | Foreign key to `sensor_location.sensor_id` |
| sensing_date | DATE | Not null |
| hour_of_day | SMALLINT | Not null, check between 0 and 23 |
| direction_1_count | INTEGER | Nullable, check greater than or equal to zero |
| direction_2_count | INTEGER | Nullable, check greater than or equal to zero |
| total_count | INTEGER | Not null, check greater than or equal to zero |
| source_record_id | VARCHAR(255) | Nullable |
| data_source | VARCHAR(255) | Nullable; row-level provenance used by prediction validation |

Primary key:
- `historical_count_id`

Foreign keys:
- `sensor_id` references `sensor_location.sensor_id`

Unique constraints:
- `sensor_id`, `sensing_date`, `hour_of_day`

Check constraints:
- `hour_of_day BETWEEN 0 AND 23`
- `direction_1_count >= 0` when present
- `direction_2_count >= 0` when present
- `total_count >= 0`

### realtime_pedestrian_count

Stores real-time or near-real-time sensor readings. It uses a single `sensed_at` timestamp instead of separate date and time fields.

| Column | Type | Constraints |
| --- | --- | --- |
| realtime_count_id | BIGINT | Primary key, identity |
| sensor_id | BIGINT | Foreign key to `sensor_location.sensor_id` |
| sensed_at | TIMESTAMPTZ | Not null |
| direction_1_count | INTEGER | Nullable, check greater than or equal to zero |
| direction_2_count | INTEGER | Nullable, check greater than or equal to zero |
| total_count | INTEGER | Not null, check greater than or equal to zero |
| source_record_id | VARCHAR(255) | Nullable |
| data_source | VARCHAR(255) | Nullable; row-level provenance used by prediction validation |

Primary key:
- `realtime_count_id`

Foreign keys:
- `sensor_id` references `sensor_location.sensor_id`

Check constraints:
- `direction_1_count >= 0` when present
- `direction_2_count >= 0` when present
- `total_count >= 0`

### route_sensor_score

Links route segments to nearby or relevant pedestrian sensors and records how each sensor contributed to the segment sensory score.

| Column | Type | Constraints |
| --- | --- | --- |
| route_sensor_score_id | BIGINT | Primary key, identity |
| route_segment_id | BIGINT | Foreign key to `route_segment.route_segment_id` |
| sensor_id | BIGINT | Foreign key to `sensor_location.sensor_id` |
| count_source | VARCHAR(30) | Not null |
| observed_at | TIMESTAMPTZ | Nullable |
| count_used | INTEGER | Nullable |
| score_contribution | NUMERIC(6,2) | Not null |

Primary key:
- `route_sensor_score_id`

Foreign keys:
- `route_segment_id` references `route_segment.route_segment_id`
- `sensor_id` references `sensor_location.sensor_id`

### alert

Stores route-level and optional segment- or sensor-specific alerts.

| Column | Type | Constraints |
| --- | --- | --- |
| alert_id | BIGINT | Primary key, identity |
| route_id | BIGINT | Foreign key to `route_option.route_id` |
| route_segment_id | BIGINT | Nullable foreign key to `route_segment.route_segment_id` |
| sensor_id | BIGINT | Nullable foreign key to `sensor_location.sensor_id` |
| alert_type | VARCHAR(50) | Not null |
| severity | VARCHAR(20) | Not null |
| message | TEXT | Not null |
| status | VARCHAR(20) | Not null |
| created_at | TIMESTAMPTZ | Not null |
| expires_at | TIMESTAMPTZ | Nullable |
| acknowledged_at | TIMESTAMPTZ | Nullable |

Primary key:
- `alert_id`

Foreign keys:
- `route_id` references `route_option.route_id`
- `route_segment_id` references `route_segment.route_segment_id`
- `sensor_id` references `sensor_location.sensor_id`

### point_of_interest

Stores places that may be used as sensory refuges or contextual points of interest.

| Column | Type | Constraints |
| --- | --- | --- |
| poi_id | BIGINT | Primary key, identity |
| theme | VARCHAR(100) | Nullable |
| sub_theme | VARCHAR(100) | Nullable |
| feature_name | VARCHAR(255) | Not null |
| address | TEXT | Nullable |
| latitude | NUMERIC(9,6) | Not null, check between -90 and 90 |
| longitude | NUMERIC(9,6) | Not null, check between -180 and 180 |
| coordinates_text | TEXT | Nullable |
| opening_hours | TEXT | Nullable |
| is_sensory_refuge | BOOLEAN | Not null, default false |
| source | VARCHAR(100) | Nullable |
| last_updated_at | TIMESTAMPTZ | Nullable |

Primary key:
- `poi_id`

Check constraints:
- `latitude BETWEEN -90 AND 90`
- `longitude BETWEEN -180 AND 180`

### route_refuge_recommendation

Links a route option to recommended points of interest that may serve as sensory refuges.

| Column | Type | Constraints |
| --- | --- | --- |
| route_refuge_recommendation_id | BIGINT | Primary key, identity |
| route_id | BIGINT | Foreign key to `route_option.route_id` |
| poi_id | BIGINT | Foreign key to `point_of_interest.poi_id` |
| recommendation_rank | INTEGER | Not null |
| distance_from_route_m | INTEGER | Nullable |
| availability_status | VARCHAR(30) | Nullable |
| created_at | TIMESTAMPTZ | Not null |

Primary key:
- `route_refuge_recommendation_id`

Foreign keys:
- `route_id` references `route_option.route_id`
- `poi_id` references `point_of_interest.poi_id`

Unique constraints:
- `route_id`, `poi_id`

### transport_stop

Stores public-transport stop reference data. The `mode` column is not part of the primary key.

| Column | Type | Constraints |
| --- | --- | --- |
| stop_id | VARCHAR(100) | Primary key |
| mode | VARCHAR(30) | Not null |
| stop_name | VARCHAR(255) | Not null |
| latitude | NUMERIC(9,6) | Not null, check between -90 and 90 |
| longitude | NUMERIC(9,6) | Not null, check between -180 and 180 |

Primary key:
- `stop_id`

Check constraints:
- `latitude BETWEEN -90 AND 90`
- `longitude BETWEEN -180 AND 180`

### route_transport_stop

Associates route options with nearby or included public-transport stops.

| Column | Type | Constraints |
| --- | --- | --- |
| route_id | BIGINT | Foreign key to `route_option.route_id`, part of composite primary key |
| stop_id | VARCHAR(100) | Foreign key to `transport_stop.stop_id`, part of composite primary key |
| stop_sequence | INTEGER | Not null, part of composite primary key |
| stop_role | VARCHAR(30) | Nullable |
| distance_m | INTEGER | Nullable |

Primary key:
- `route_id`, `stop_id`, `stop_sequence`

Foreign keys:
- `route_id` references `route_option.route_id`
- `stop_id` references `transport_stop.stop_id`

### journey_feedback

Stores anonymous feedback about a completed or reviewed route.

| Column | Type | Constraints |
| --- | --- | --- |
| feedback_id | BIGINT | Primary key, identity |
| route_id | BIGINT | Foreign key to `route_option.route_id` |
| session_id | UUID | Not null |
| sensory_rating | SMALLINT | Not null, check between 1 and 5 |
| crowd_rating | SMALLINT | Nullable, check between 1 and 5 when present |
| comments | TEXT | Nullable |
| submitted_at | TIMESTAMPTZ | Not null |

Primary key:
- `feedback_id`

Foreign keys:
- `route_id` references `route_option.route_id`

Check constraints:
- `sensory_rating BETWEEN 1 AND 5`
- `crowd_rating BETWEEN 1 AND 5` when present

## Relationships

- `user_preference` has many `journey_request` records.
- `journey_request` has many `route_option` records.
- `route_option` has many `route_segment` records.
- `route_segment` has many `route_sensor_score` records.
- `sensor_location` has many `historical_pedestrian_count` records.
- `sensor_location` has many `realtime_pedestrian_count` records.
- `sensor_location` has many `route_sensor_score` records.
- `route_option` has many `alert` records.
- `route_segment` may have many `alert` records.
- `sensor_location` may have many `alert` records.
- `route_option` has many `route_refuge_recommendation` records.
- `point_of_interest` has many `route_refuge_recommendation` records.
- `route_option` has many `route_transport_stop` records.
- `transport_stop` has many `route_transport_stop` records.
- `route_option` has many `journey_feedback` records.

## Deletion Behaviour

Use `CASCADE` where child records cannot exist meaningfully without their parent:

- `journey_request` to `route_option`
- `route_option` to `route_segment`
- `route_segment` to `route_sensor_score`
- `route_option` to `route_refuge_recommendation`
- `route_option` to `route_transport_stop`

Use `RESTRICT` or `NO ACTION` for shared reference data:

- `sensor_location`
- `point_of_interest`
- `transport_stop`

Additional guidance:

- Deleting a `route_option` should remove its dependent route segments, refuge recommendations, transport-stop links, and route-level alerts if those alerts are treated as route output records.
- Deleting shared reference rows should be restricted while count records, route scores, alerts, or recommendations still reference them.
- The deletion behaviour for `user_preference` to `journey_request` is intentionally conservative and should be finalized when retention requirements for anonymous sessions are known.

## Recommended Indexes

Create indexes for all foreign-key columns:

- `journey_request.preference_id`
- `route_option.journey_request_id`
- `route_segment.route_id`
- `historical_pedestrian_count.sensor_id`
- `realtime_pedestrian_count.sensor_id`
- `route_sensor_score.route_segment_id`
- `route_sensor_score.sensor_id`
- `alert.route_id`
- `alert.route_segment_id`
- `alert.sensor_id`
- `route_refuge_recommendation.route_id`
- `route_refuge_recommendation.poi_id`
- `route_transport_stop.route_id`
- `route_transport_stop.stop_id`
- `journey_feedback.route_id`

Create these query-focused indexes:

- `sensor_location.latitude`, `sensor_location.longitude`
- `historical_pedestrian_count.sensor_id`, `historical_pedestrian_count.sensing_date`, `historical_pedestrian_count.hour_of_day`
- `realtime_pedestrian_count.sensor_id`, `realtime_pedestrian_count.sensed_at`
- `route_segment.route_id`, `route_segment.segment_sequence`
- `alert.route_id`, `alert.status`, `alert.created_at`
- `point_of_interest.latitude`, `point_of_interest.longitude`
- `journey_feedback.route_id`, `journey_feedback.submitted_at`

## Capability Confirmation

This schema supports:

- Multiple route alternatives through `journey_request` and `route_option`.
- Sensory scoring through `route_option.total_sensory_score`, `route_segment.sensory_score`, and `route_sensor_score`.
- Congested route segments through `route_segment.congestion_level`.
- Historical pedestrian counts through `historical_pedestrian_count`.
- Real-time pedestrian counts through `realtime_pedestrian_count`.
- Alerts through `alert`.
- Refuge recommendations through `point_of_interest` and `route_refuge_recommendation`.
- Public-transport stops through `transport_stop` and `route_transport_stop`.
- Journey feedback through `journey_feedback`.

## Open Design Decisions

- `preference_id` on `journey_request` is specified as a foreign key but not explicitly marked `NOT NULL`; this should be confirmed before implementation.
- Controlled vocabularies for fields such as `travel_mode`, `sensory_indicator`, `data_availability_status`, `status`, `severity`, `count_source`, and `stop_role` should be finalized before adding check constraints or lookup tables.
- Spatial indexing strategy is not defined yet. Standard latitude/longitude indexes are documented here, but future implementation may consider PostGIS if spatial queries become central.
- Retention and deletion rules for anonymous sessions, journey requests, alerts, and feedback should be confirmed before migrations are created.
