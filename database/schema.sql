CREATE DATABASE IF NOT EXISTS escape_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE escape_db;

CREATE TABLE point_of_interest (
  poi_id BIGINT NOT NULL AUTO_INCREMENT,
  theme VARCHAR(100) NULL,
  sub_theme VARCHAR(100) NULL,
  feature_name VARCHAR(255) NOT NULL,
  address TEXT NULL,
  latitude DECIMAL(9, 6) NOT NULL,
  longitude DECIMAL(9, 6) NOT NULL,
  coordinates_text TEXT NULL,
  opening_hours TEXT NULL,
  is_sensory_refuge BOOLEAN NOT NULL DEFAULT FALSE,
  source VARCHAR(100) NULL,
  source_record_id VARCHAR(255) NULL,
  accessibility_notes TEXT NULL,
  sensory_notes TEXT NULL,
  last_updated_at DATETIME NULL,
  PRIMARY KEY (poi_id),
  CONSTRAINT ck_point_of_interest_latitude_range CHECK (latitude BETWEEN -90 AND 90),
  CONSTRAINT ck_point_of_interest_longitude_range CHECK (longitude BETWEEN -180 AND 180),
  CONSTRAINT uq_point_of_interest_source_record_id UNIQUE (source, source_record_id),
  INDEX ix_point_of_interest_latitude_longitude (latitude, longitude)
) ENGINE=InnoDB;

CREATE TABLE sensor_location (
  sensor_id BIGINT NOT NULL AUTO_INCREMENT,
  sensor_name VARCHAR(255) NOT NULL,
  description TEXT NULL,
  location_name VARCHAR(255) NULL,
  location_type VARCHAR(50) NULL,
  latitude DECIMAL(9, 6) NOT NULL,
  longitude DECIMAL(9, 6) NOT NULL,
  installation_date DATE NULL,
  status VARCHAR(30) NOT NULL,
  direction_1 VARCHAR(100) NULL,
  direction_2 VARCHAR(100) NULL,
  source VARCHAR(100) NULL,
  last_updated_at DATETIME NULL,
  PRIMARY KEY (sensor_id),
  CONSTRAINT ck_sensor_location_latitude_range CHECK (latitude BETWEEN -90 AND 90),
  CONSTRAINT ck_sensor_location_longitude_range CHECK (longitude BETWEEN -180 AND 180),
  INDEX ix_sensor_location_latitude_longitude (latitude, longitude)
) ENGINE=InnoDB;

CREATE TABLE transport_stop (
  stop_id VARCHAR(100) NOT NULL,
  mode VARCHAR(30) NOT NULL,
  stop_name VARCHAR(255) NOT NULL,
  latitude DECIMAL(9, 6) NOT NULL,
  longitude DECIMAL(9, 6) NOT NULL,
  PRIMARY KEY (stop_id),
  CONSTRAINT ck_transport_stop_latitude_range CHECK (latitude BETWEEN -90 AND 90),
  CONSTRAINT ck_transport_stop_longitude_range CHECK (longitude BETWEEN -180 AND 180),
  INDEX ix_transport_stop_latitude_longitude (latitude, longitude)
) ENGINE=InnoDB;

CREATE TABLE user_preference (
  preference_id BIGINT NOT NULL AUTO_INCREMENT,
  session_id CHAR(32) NOT NULL,
  preferred_crowd_threshold SMALLINT NOT NULL,
  notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  search_radius_m INT NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (preference_id),
  CONSTRAINT ck_user_preference_preferred_crowd_threshold_range CHECK (preferred_crowd_threshold BETWEEN 1 AND 5),
  CONSTRAINT ck_user_preference_search_radius_m_positive CHECK (search_radius_m > 0),
  UNIQUE KEY uq_user_preference_session_id (session_id),
  INDEX ix_user_preference_session_id (session_id)
) ENGINE=InnoDB;

CREATE TABLE historical_pedestrian_count (
  historical_count_id BIGINT NOT NULL AUTO_INCREMENT,
  sensor_id BIGINT NOT NULL,
  sensing_date DATE NOT NULL,
  hour_of_day SMALLINT NOT NULL,
  direction_1_count INT NULL,
  direction_2_count INT NULL,
  total_count INT NOT NULL,
  source_record_id VARCHAR(255) NULL,
  data_source VARCHAR(255) NULL,
  PRIMARY KEY (historical_count_id),
  CONSTRAINT uq_historical_pedestrian_count_sensor_date_hour UNIQUE (sensor_id, sensing_date, hour_of_day),
  CONSTRAINT ck_historical_pedestrian_count_hour_of_day_range CHECK (hour_of_day BETWEEN 0 AND 23),
  CONSTRAINT ck_historical_pedestrian_count_direction_1_non_negative CHECK (direction_1_count IS NULL OR direction_1_count >= 0),
  CONSTRAINT ck_historical_pedestrian_count_direction_2_non_negative CHECK (direction_2_count IS NULL OR direction_2_count >= 0),
  CONSTRAINT ck_historical_pedestrian_count_total_non_negative CHECK (total_count >= 0),
  CONSTRAINT fk_historical_pedestrian_count_sensor
    FOREIGN KEY (sensor_id) REFERENCES sensor_location (sensor_id)
    ON DELETE RESTRICT,
  INDEX ix_historical_pedestrian_count_sensor_id (sensor_id),
  INDEX ix_historical_pedestrian_count_sensor_date_hour (sensor_id, sensing_date, hour_of_day)
) ENGINE=InnoDB;

CREATE TABLE journey_request (
  journey_request_id BIGINT NOT NULL AUTO_INCREMENT,
  preference_id BIGINT NULL,
  origin_latitude DECIMAL(9, 6) NOT NULL,
  origin_longitude DECIMAL(9, 6) NOT NULL,
  destination_latitude DECIMAL(9, 6) NOT NULL,
  destination_longitude DECIMAL(9, 6) NOT NULL,
  travel_mode VARCHAR(30) NOT NULL,
  preferred_crowd_threshold SMALLINT NOT NULL,
  requested_at DATETIME NOT NULL,
  PRIMARY KEY (journey_request_id),
  CONSTRAINT ck_journey_request_origin_latitude_range CHECK (origin_latitude BETWEEN -90 AND 90),
  CONSTRAINT ck_journey_request_origin_longitude_range CHECK (origin_longitude BETWEEN -180 AND 180),
  CONSTRAINT ck_journey_request_destination_latitude_range CHECK (destination_latitude BETWEEN -90 AND 90),
  CONSTRAINT ck_journey_request_destination_longitude_range CHECK (destination_longitude BETWEEN -180 AND 180),
  CONSTRAINT ck_journey_request_preferred_crowd_threshold_range CHECK (preferred_crowd_threshold BETWEEN 1 AND 5),
  CONSTRAINT fk_journey_request_preference
    FOREIGN KEY (preference_id) REFERENCES user_preference (preference_id)
    ON DELETE RESTRICT,
  INDEX ix_journey_request_preference_id (preference_id)
) ENGINE=InnoDB;

CREATE TABLE realtime_pedestrian_count (
  realtime_count_id BIGINT NOT NULL AUTO_INCREMENT,
  sensor_id BIGINT NOT NULL,
  sensed_at DATETIME NOT NULL,
  direction_1_count INT NULL,
  direction_2_count INT NULL,
  total_count INT NOT NULL,
  source_record_id VARCHAR(255) NULL,
  data_source VARCHAR(255) NULL,
  PRIMARY KEY (realtime_count_id),
  CONSTRAINT ck_realtime_pedestrian_count_direction_1_non_negative CHECK (direction_1_count IS NULL OR direction_1_count >= 0),
  CONSTRAINT ck_realtime_pedestrian_count_direction_2_non_negative CHECK (direction_2_count IS NULL OR direction_2_count >= 0),
  CONSTRAINT ck_realtime_pedestrian_count_total_non_negative CHECK (total_count >= 0),
  CONSTRAINT fk_realtime_pedestrian_count_sensor
    FOREIGN KEY (sensor_id) REFERENCES sensor_location (sensor_id)
    ON DELETE RESTRICT,
  INDEX ix_realtime_pedestrian_count_sensor_id (sensor_id),
  INDEX ix_realtime_pedestrian_count_sensor_id_sensed_at (sensor_id, sensed_at)
) ENGINE=InnoDB;

CREATE TABLE refuge_feedback (
  feedback_id BIGINT NOT NULL AUTO_INCREMENT,
  refuge_id BIGINT NOT NULL,
  quietness_score SMALLINT NOT NULL,
  crowding_level VARCHAR(20) NOT NULL,
  comfort_level VARCHAR(20) NOT NULL,
  comment TEXT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (feedback_id),
  CONSTRAINT ck_refuge_feedback_quietness_range CHECK (quietness_score BETWEEN 1 AND 5),
  CONSTRAINT ck_refuge_feedback_crowding_level CHECK (crowding_level IN ('low', 'moderate', 'high')),
  CONSTRAINT ck_refuge_feedback_comfort_level CHECK (comfort_level IN ('yes', 'somewhat', 'no')),
  CONSTRAINT fk_refuge_feedback_refuge
    FOREIGN KEY (refuge_id) REFERENCES point_of_interest (poi_id)
    ON DELETE CASCADE,
  INDEX ix_refuge_feedback_refuge_id (refuge_id),
  INDEX ix_refuge_feedback_refuge_id_created_at (refuge_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE sensory_prediction (
  prediction_id BIGINT NOT NULL AUTO_INCREMENT,
  sensor_id BIGINT NOT NULL,
  prediction_for DATETIME NOT NULL,
  predicted_count INT NULL,
  severity VARCHAR(20) NOT NULL,
  confidence VARCHAR(20) NOT NULL,
  generated_at DATETIME NOT NULL,
  source_freshness VARCHAR(20) NOT NULL,
  model_version VARCHAR(50) NOT NULL,
  data_availability_status VARCHAR(30) NOT NULL,
  limitation_message TEXT NULL,
  source_validated BOOLEAN NOT NULL,
  PRIMARY KEY (prediction_id),
  CONSTRAINT uq_sensory_prediction_sensor_target_model UNIQUE (sensor_id, prediction_for, model_version),
  CONSTRAINT fk_sensory_prediction_sensor
    FOREIGN KEY (sensor_id) REFERENCES sensor_location (sensor_id)
    ON DELETE RESTRICT,
  INDEX ix_sensory_prediction_prediction_for (prediction_for),
  INDEX ix_sensory_prediction_sensor_id (sensor_id)
) ENGINE=InnoDB;

CREATE TABLE route_option (
  route_id BIGINT NOT NULL AUTO_INCREMENT,
  journey_request_id BIGINT NOT NULL,
  google_route_id VARCHAR(255) NULL,
  encoded_polyline TEXT NULL,
  estimated_travel_minutes INT NOT NULL,
  sensory_indicator VARCHAR(20) NOT NULL,
  total_sensory_score DECIMAL(6, 2) NULL,
  data_availability_status VARCHAR(30) NOT NULL,
  is_recommended BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL,
  expires_at DATETIME NULL,
  PRIMARY KEY (route_id),
  CONSTRAINT fk_route_option_journey_request
    FOREIGN KEY (journey_request_id) REFERENCES journey_request (journey_request_id)
    ON DELETE CASCADE,
  INDEX ix_route_option_journey_request_id (journey_request_id)
) ENGINE=InnoDB;

CREATE TABLE journey_feedback (
  feedback_id BIGINT NOT NULL AUTO_INCREMENT,
  route_id BIGINT NOT NULL,
  session_id CHAR(32) NOT NULL,
  sensory_rating SMALLINT NOT NULL,
  crowd_rating SMALLINT NULL,
  comments TEXT NULL,
  submitted_at DATETIME NOT NULL,
  PRIMARY KEY (feedback_id),
  CONSTRAINT ck_journey_feedback_sensory_rating_range CHECK (sensory_rating BETWEEN 1 AND 5),
  CONSTRAINT ck_journey_feedback_crowd_rating_range CHECK (crowd_rating IS NULL OR crowd_rating BETWEEN 1 AND 5),
  CONSTRAINT fk_journey_feedback_route
    FOREIGN KEY (route_id) REFERENCES route_option (route_id)
    ON DELETE CASCADE,
  INDEX ix_journey_feedback_route_id (route_id),
  INDEX ix_journey_feedback_route_id_submitted_at (route_id, submitted_at)
) ENGINE=InnoDB;

CREATE TABLE route_refuge_recommendation (
  route_refuge_recommendation_id BIGINT NOT NULL AUTO_INCREMENT,
  route_id BIGINT NOT NULL,
  poi_id BIGINT NOT NULL,
  recommendation_rank INT NOT NULL,
  distance_from_route_m INT NULL,
  availability_status VARCHAR(30) NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (route_refuge_recommendation_id),
  CONSTRAINT uq_route_refuge_recommendation_route_id_poi_id UNIQUE (route_id, poi_id),
  CONSTRAINT fk_route_refuge_recommendation_route
    FOREIGN KEY (route_id) REFERENCES route_option (route_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_route_refuge_recommendation_poi
    FOREIGN KEY (poi_id) REFERENCES point_of_interest (poi_id)
    ON DELETE RESTRICT,
  INDEX ix_route_refuge_recommendation_route_id (route_id),
  INDEX ix_route_refuge_recommendation_poi_id (poi_id)
) ENGINE=InnoDB;

CREATE TABLE route_segment (
  route_segment_id BIGINT NOT NULL AUTO_INCREMENT,
  route_id BIGINT NOT NULL,
  segment_sequence INT NOT NULL,
  encoded_polyline TEXT NULL,
  distance_m INT NULL,
  duration_seconds INT NULL,
  congestion_level VARCHAR(20) NULL,
  sensory_score DECIMAL(6, 2) NULL,
  data_availability_status VARCHAR(30) NULL,
  PRIMARY KEY (route_segment_id),
  CONSTRAINT uq_route_segment_route_id_segment_sequence UNIQUE (route_id, segment_sequence),
  CONSTRAINT fk_route_segment_route
    FOREIGN KEY (route_id) REFERENCES route_option (route_id)
    ON DELETE CASCADE,
  INDEX ix_route_segment_route_id (route_id),
  INDEX ix_route_segment_route_id_segment_sequence (route_id, segment_sequence)
) ENGINE=InnoDB;

CREATE TABLE route_transport_stop (
  route_id BIGINT NOT NULL,
  stop_id VARCHAR(100) NOT NULL,
  stop_sequence INT NOT NULL,
  stop_role VARCHAR(30) NULL,
  distance_m INT NULL,
  PRIMARY KEY (route_id, stop_id, stop_sequence),
  CONSTRAINT fk_route_transport_stop_route
    FOREIGN KEY (route_id) REFERENCES route_option (route_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_route_transport_stop_stop
    FOREIGN KEY (stop_id) REFERENCES transport_stop (stop_id)
    ON DELETE RESTRICT,
  INDEX ix_route_transport_stop_route_id (route_id),
  INDEX ix_route_transport_stop_stop_id (stop_id)
) ENGINE=InnoDB;

CREATE TABLE alert (
  alert_id BIGINT NOT NULL AUTO_INCREMENT,
  route_id BIGINT NULL,
  route_segment_id BIGINT NULL,
  sensor_id BIGINT NULL,
  prediction_id BIGINT NULL,
  deduplication_key VARCHAR(255) NULL,
  alert_type VARCHAR(50) NOT NULL,
  severity VARCHAR(20) NOT NULL,
  message TEXT NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NULL,
  expires_at DATETIME NULL,
  acknowledged_at DATETIME NULL,
  PRIMARY KEY (alert_id),
  CONSTRAINT fk_alert_route
    FOREIGN KEY (route_id) REFERENCES route_option (route_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_alert_route_segment
    FOREIGN KEY (route_segment_id) REFERENCES route_segment (route_segment_id)
    ON DELETE SET NULL,
  CONSTRAINT fk_alert_sensor
    FOREIGN KEY (sensor_id) REFERENCES sensor_location (sensor_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_alert_prediction
    FOREIGN KEY (prediction_id) REFERENCES sensory_prediction (prediction_id)
    ON DELETE SET NULL,
  INDEX ix_alert_route_id (route_id),
  INDEX ix_alert_route_segment_id (route_segment_id),
  INDEX ix_alert_sensor_id (sensor_id),
  INDEX ix_alert_route_id_status_created_at (route_id, status, created_at),
  INDEX ix_alert_deduplication_key (deduplication_key)
) ENGINE=InnoDB;

CREATE TABLE route_sensor_score (
  route_sensor_score_id BIGINT NOT NULL AUTO_INCREMENT,
  route_segment_id BIGINT NOT NULL,
  sensor_id BIGINT NOT NULL,
  count_source VARCHAR(30) NOT NULL,
  observed_at DATETIME NULL,
  count_used INT NULL,
  score_contribution DECIMAL(6, 2) NOT NULL,
  PRIMARY KEY (route_sensor_score_id),
  CONSTRAINT fk_route_sensor_score_route_segment
    FOREIGN KEY (route_segment_id) REFERENCES route_segment (route_segment_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_route_sensor_score_sensor
    FOREIGN KEY (sensor_id) REFERENCES sensor_location (sensor_id)
    ON DELETE RESTRICT,
  INDEX ix_route_sensor_score_route_segment_id (route_segment_id),
  INDEX ix_route_sensor_score_sensor_id (sensor_id)
) ENGINE=InnoDB;
