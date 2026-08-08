USE escape_db;

SHOW TABLES;

SELECT COUNT(*) AS sensor_location_count FROM sensor_location;
SELECT COUNT(*) AS point_of_interest_count FROM point_of_interest;
SELECT COUNT(*) AS transport_stop_count FROM transport_stop;
SELECT COUNT(*) AS realtime_pedestrian_count_count FROM realtime_pedestrian_count;
SELECT COUNT(*) AS historical_pedestrian_count_count FROM historical_pedestrian_count;
