"use client";

import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Circle,
  CircleMarker,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";

import L from "leaflet";

import "leaflet/dist/leaflet.css";

const MELBOURNE_CBD_CENTER = [-37.8136, 144.9631];
const START_ICON = L.divIcon({
  className: "route-endpoint-icon",
  html: '<span class="route-endpoint-icon__start"></span>',
  iconSize: [26, 26],
  iconAnchor: [13, 13],
  popupAnchor: [0, -14],
});
const DESTINATION_ICON = L.divIcon({
  className: "route-endpoint-icon",
  html: '<span class="route-endpoint-icon__destination"></span>',
  iconSize: [34, 42],
  iconAnchor: [17, 39],
  popupAnchor: [0, -38],
});

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
  showCrowdAreas = false,
  expanded = false,
}) {
  const selectedRoute = routes.find(
    (route) => route.route_identifier === selectedRouteIdentifier
  );
  const endpointRoute = selectedRoute || routes.find((route) => route.is_recommended) || routes[0];
  const routeStart = endpointRoute?.points?.[0];
  const routeDestination = endpointRoute?.points?.[endpointRoute.points.length - 1];
  const matchedSensors = Array.from((selectedRoute?.route_segments || []).reduce(
    (sensors, segment) => {
      (segment.matched_sensors || []).forEach((sensor) => {
        const current = sensors.get(sensor.sensor_id);
        const congestionLevel = segment.congestion_level || "unavailable";
        if (!current || crowdSeverity(congestionLevel) > crowdSeverity(current.congestionLevel)) {
          sensors.set(sensor.sensor_id, { ...sensor, congestionLevel });
        }
      });
      return sensors;
    },
    new Map()
  ).values());

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

        {showCrowdAreas && matchedSensors.map((sensor) => {
          if (!CROWD_AREA_COLORS[sensor.congestionLevel]) return null;
          const count = Number(sensor.pedestrian_count);
          const radius = Number.isFinite(count)
            ? Math.min(140, 55 + Math.sqrt(Math.max(count, 0)) * 4)
            : 65;
          return (
            <Circle
              key={`crowd-area-${sensor.sensor_id}`}
              center={[sensor.latitude, sensor.longitude]}
              radius={radius}
              interactive={false}
              pathOptions={{
                color: CROWD_AREA_COLORS[sensor.congestionLevel],
                weight: 0,
                fillColor: CROWD_AREA_COLORS[sensor.congestionLevel],
                fillOpacity: sensor.congestionLevel === "high"
                  ? 0.3
                  : sensor.congestionLevel === "low"
                    ? 0.18
                    : 0.24,
              }}
            />
          );
        })}

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

        {routeStart ? (
          <Marker position={routeStart} icon={START_ICON} zIndexOffset={900}>
            <Popup><strong>Starting location</strong></Popup>
          </Marker>
        ) : null}
        {routeDestination ? (
          <Marker position={routeDestination} icon={DESTINATION_ICON} zIndexOffset={1000}>
            <Popup><strong>Destination</strong></Popup>
          </Marker>
        ) : null}
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

const CROWD_AREA_COLORS = {
  low: "#3f9b78",
  medium: "#d89b2b",
  moderate: "#d89b2b",
  high: "#d94f4f",
};

const CROWD_SEVERITY = {
  unavailable: 0,
  low: 1,
  medium: 2,
  moderate: 2,
  high: 3,
};

function crowdSeverity(level) {
  return CROWD_SEVERITY[level] || 0;
}
