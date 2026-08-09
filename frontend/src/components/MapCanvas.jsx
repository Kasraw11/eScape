"use client";

import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Popup,
  useMap,
} from "react-leaflet";

import L from "leaflet";

import "leaflet/dist/leaflet.css";

const MELBOURNE_CBD_CENTER = [-37.8136, 144.9631];

/**
 * Automatically fits the map around all returned routes.
 */
function FitRouteBounds({ routes, expanded }) {
  const map = useMap();

  useEffect(() => {
    const points = routes.flatMap(
      (route) => route.points || []
    );

    if (!points.length) {
      map.setView(MELBOURNE_CBD_CENTER, 15);
      return;
    }

    const bounds = L.latLngBounds(
      points.map(([lat, lng]) => [lat, lng])
    );

    map.fitBounds(bounds, {
      padding: expanded ? [60, 60] : [30, 30],
    });
  }, [map, routes, expanded]);

  return null;
}

/**
 * Returns the visual style for a route.
 */
function routeStyle(route, selected) {
  if (selected) {
    return {
      weight: 7,
      opacity: 1,
    };
  }

  if (route.is_recommended) {
    return {
      weight: 5,
      opacity: 0.8,
    };
  }

  return {
    weight: 4,
    opacity: 0.5,
  };
}

/**
 * Draws OSRM routes using OpenStreetMap.
 */
export default function MapCanvas({
  routes = [],
  selectedRouteIdentifier,
  onSelectRoute,
  expanded = false,
}) {
  const selectedRoute = routes.find(
    (route) => route.route_identifier === selectedRouteIdentifier
  );
  const matchedSensors = Array.from(
    new Map(
      (selectedRoute?.route_segments || [])
        .flatMap((segment) => segment.matched_sensors || [])
        .map((sensor) => [sensor.sensor_id, sensor])
    ).values()
  );

  return (
        <div
          className={
            expanded
              ? "map-canvas map-canvas--expanded"
              : "map-canvas"
          }
          style={{
            width: "100%",
            height: expanded ? "70vh" : "100%",
            minHeight: expanded ? "70vh" : "400px",
            overflow: "hidden",
            borderRadius: "14px",
          }}
        >
          <MapContainer
            center={MELBOURNE_CBD_CENTER}
            zoom={15}
            scrollWheelZoom={true}
            style={{
              width: "100%",
              height: "100%",
            }}
          >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <FitRouteBounds
          routes={routes}
          expanded={expanded}
        />

        {routes.map((route) => {
          const selected =
            route.route_identifier ===
            selectedRouteIdentifier;

          const positions = (
            route.points || []
          ).map(([lat, lng]) => [lat, lng]);

          if (positions.length < 2) {
            return null;
          }

          return (
            <Polyline
              key={route.route_identifier}
              positions={positions}
              pathOptions={routeStyle(
                route,
                selected
              )}
              eventHandlers={{
                click: () =>
                  onSelectRoute?.(
                    route.route_identifier
                  ),
              }}
            />
          );
        })}

        {(selectedRoute?.route_segments || []).map((segment) => {
          const positions = (segment.points || []).map(
            ([lat, lng]) => [lat, lng]
          );
          if (positions.length < 2) return null;
          return (
            <Polyline
              key={`crowd-${segment.segment_sequence}`}
              positions={positions}
              pathOptions={{
                color: CROWD_COLORS[segment.congestion_level] || "#4f6bed",
                weight: 7,
                opacity: 0.9,
              }}
            />
          );
        })}

        {matchedSensors.map((sensor) => (
          <CircleMarker
            key={`sensor-${sensor.sensor_id}`}
            center={[sensor.latitude, sensor.longitude]}
            radius={6}
            pathOptions={{
              color: "#ffffff",
              weight: 2,
              fillColor: "#173f5f",
              fillOpacity: 1,
            }}
          >
            <Popup>
              <strong>{sensor.sensor_name}</strong><br />
              {sensor.pedestrian_count == null
                ? "Latest count unavailable"
                : `${sensor.pedestrian_count} pedestrians in the latest reading`}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}

const CROWD_COLORS = {
  low: "#2f855a",
  medium: "#b7791f",
  moderate: "#b7791f",
  high: "#c53030",
};
