CREATE DATABASE IF NOT EXISTS escape_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE escape_db;

CREATE TABLE sensor_location (
  sensor_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  sensor_name VARCHAR(150) NOT NULL,
  description TEXT NULL,
  location VARCHAR(255) NOT NULL,
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10,7) NOT NULL,
  location_type VARCHAR(80) NULL,
  installation_date DATE NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'active',
  direction_1 VARCHAR(120) NULL,
  direction_2 VARCHAR(120) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (sensor_id),
  INDEX idx_sensor_location_status (status),
  INDEX idx_sensor_location_type (location_type)
) ENGINE=InnoDB;

CREATE TABLE transport_stop (
  stop_id VARCHAR(80) NOT NULL,
  mode VARCHAR(40) NOT NULL,
  stop_name VARCHAR(180) NOT NULL,
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  PRIMARY KEY (stop_id, mode),
  INDEX idx_transport_stop_mode (mode),
  INDEX idx_transport_stop_position (latitude, longitude)
) ENGINE=InnoDB;

CREATE TABLE historical_pedestrian_count (
  location_id INT UNSIGNED NOT NULL,
  sensing_date DATE NOT NULL,
  hour_day TINYINT UNSIGNED NOT NULL,
  source_record_id VARCHAR(120) NULL,
  direction_1_count INT UNSIGNED NOT NULL DEFAULT 0,
  direction_2_count INT UNSIGNED NOT NULL DEFAULT 0,
  total_count INT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (location_id, sensing_date, hour_day),
  CONSTRAINT chk_historical_hour_day CHECK (hour_day BETWEEN 0 AND 23),
  CONSTRAINT fk_historical_location
    FOREIGN KEY (location_id) REFERENCES sensor_location (sensor_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE realtime_pedestrian_count (
  realtime_count_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  location_id INT UNSIGNED NOT NULL,
  sensing_datetime DATETIME NOT NULL,
  sensing_date DATE NOT NULL,
  sensing_time TIME NOT NULL,
  direction_1_count INT UNSIGNED NOT NULL DEFAULT 0,
  direction_2_count INT UNSIGNED NOT NULL DEFAULT 0,
  total_count INT UNSIGNED NOT NULL DEFAULT 0,
  duplicate_sequence SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (realtime_count_id),
  UNIQUE KEY uq_realtime_location_datetime_duplicate (
    location_id,
    sensing_datetime,
    duplicate_sequence
  ),
  INDEX idx_realtime_location_datetime (location_id, sensing_datetime),
  CONSTRAINT fk_realtime_location
    FOREIGN KEY (location_id) REFERENCES sensor_location (sensor_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE user_preference (
  preference_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  preferred_crowd_threshold INT UNSIGNED NULL,
  notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  search_radius_m INT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (preference_id)
) ENGINE=InnoDB;

CREATE TABLE route_option (
  route_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  preference_id BIGINT UNSIGNED NOT NULL,
  origin_latitude DECIMAL(10, 7) NOT NULL,
  origin_longitude DECIMAL(10, 7) NOT NULL,
  destination_latitude DECIMAL(10, 7) NOT NULL,
  destination_longitude DECIMAL(10, 7) NOT NULL,
  estimated_travel_minutes INT UNSIGNED NULL,
  sensory_indicator VARCHAR(80) NULL,
  total_sensory_score DECIMAL(8, 2) NULL,
  data_availability_status VARCHAR(60) NULL,
  is_recommended BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (route_id),
  INDEX idx_route_preference (preference_id),
  INDEX idx_route_recommended (is_recommended),
  CONSTRAINT fk_route_preference
    FOREIGN KEY (preference_id) REFERENCES user_preference (preference_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE route_sensor_score (
  route_id BIGINT UNSIGNED NOT NULL,
  location_id INT UNSIGNED NOT NULL,
  count_source VARCHAR(40) NOT NULL,
  observation_time DATETIME NULL,
  count_used INT UNSIGNED NULL,
  score_contribution DECIMAL(8, 2) NULL,
  PRIMARY KEY (route_id, location_id),
  INDEX idx_route_sensor_location (location_id),
  CONSTRAINT fk_route_sensor_route
    FOREIGN KEY (route_id) REFERENCES route_option (route_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_route_sensor_location
    FOREIGN KEY (location_id) REFERENCES sensor_location (sensor_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE point_of_interest (
  poi_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  theme VARCHAR(100) NULL,
  sub_theme VARCHAR(100) NULL,
  feature_name VARCHAR(180) NOT NULL,
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  coordinates_text VARCHAR(255) NULL,
  is_sensory_refuge BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (poi_id),
  INDEX idx_poi_theme (theme, sub_theme),
  INDEX idx_poi_refuge (is_sensory_refuge),
  INDEX idx_poi_position (latitude, longitude)
) ENGINE=InnoDB;

CREATE TABLE alert (
  alert_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  route_id BIGINT UNSIGNED NOT NULL,
  location_id INT UNSIGNED NOT NULL,
  alert_type VARCHAR(80) NOT NULL,
  severity VARCHAR(40) NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (alert_id),
  INDEX idx_alert_route (route_id),
  INDEX idx_alert_location (location_id),
  INDEX idx_alert_created_at (created_at),
  CONSTRAINT fk_alert_route
    FOREIGN KEY (route_id) REFERENCES route_option (route_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_alert_location
    FOREIGN KEY (location_id) REFERENCES sensor_location (sensor_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE route_refuge_recommendation (
  route_id BIGINT UNSIGNED NOT NULL,
  poi_id BIGINT UNSIGNED NOT NULL,
  recommendation_rank INT UNSIGNED NULL,
  distance_from_route_m DECIMAL(10, 2) NULL,
  availability_status VARCHAR(60) NULL,
  PRIMARY KEY (route_id, poi_id),
  INDEX idx_refuge_poi (poi_id),
  INDEX idx_refuge_rank (route_id, recommendation_rank),
  CONSTRAINT fk_refuge_route
    FOREIGN KEY (route_id) REFERENCES route_option (route_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_refuge_poi
    FOREIGN KEY (poi_id) REFERENCES point_of_interest (poi_id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE route_transport_stop (
  route_id BIGINT UNSIGNED NOT NULL,
  stop_id VARCHAR(80) NOT NULL,
  mode VARCHAR(40) NOT NULL,
  stop_role VARCHAR(40) NOT NULL,
  distance_m DECIMAL(10, 2) NULL,
  PRIMARY KEY (route_id, stop_id, mode),
  INDEX idx_route_stop_stop (stop_id, mode),
  CONSTRAINT fk_route_stop_route
    FOREIGN KEY (route_id) REFERENCES route_option (route_id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_route_stop_transport_stop
    FOREIGN KEY (stop_id, mode) REFERENCES transport_stop (stop_id, mode)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;
