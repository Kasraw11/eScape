"use client";

import { useEffect } from "react";
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";

import "leaflet/dist/leaflet.css";

const MELBOURNE_CBD_CENTER = [-37.8136, 144.9631];
const COLORS = {
  Park: "#15803d",
  Library: "#2563eb",
  "Quiet public space": "#7c3aed",
  "Indoor quiet space": "#0f766e",
  Low: "#15803d",
  Moderate: "#b45309",
  High: "#b91c1c",
  Unavailable: "#475569",
};

function FitPointBounds({ points, routePoints, expanded }) {
  const map = useMap();

  useEffect(() => {
    map.invalidateSize();
    const allPoints = [
      ...points.map((point) => [point.latitude, point.longitude]),
      ...routePoints,
    ];
    if (!allPoints.length) {
      map.setView(MELBOURNE_CBD_CENTER, 14);
      return;
    }
    if (allPoints.length === 1) {
      map.setView(allPoints[0], 16);
      return;
    }
    map.fitBounds(
      L.latLngBounds(allPoints),
      { padding: expanded ? [60, 60] : [36, 36], maxZoom: 16 }
    );
  }, [expanded, map, points, routePoints]);

  return null;
}

function LocationPicker({ onChooseLocation }) {
  useMapEvents({
    click(event) {
      onChooseLocation?.({
        latitude: event.latlng.lat,
        longitude: event.latlng.lng,
        label: "Selected map location",
      });
    },
  });
  return null;
}

export default function PointMap({
  points,
  selectedId,
  onSelect,
  onChooseLocation,
  routePoints = [],
  expanded = false,
  label = "Melbourne map",
}) {
  return (
    <div className="point-map">
      <div className="map-canvas" aria-label={label}>
        <MapContainer
          center={MELBOURNE_CBD_CENTER}
          zoom={14}
          scrollWheelZoom
          style={{ width: "100%", height: "100%", minHeight: expanded ? "70vh" : "360px" }}
        >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitPointBounds points={points} routePoints={routePoints} expanded={expanded} />
          <LocationPicker onChooseLocation={onChooseLocation} />
          {routePoints.length > 1 ? (
            <Polyline
              positions={routePoints}
              pathOptions={{ color: "#4965e8", weight: 6, opacity: 0.95 }}
            />
          ) : null}
          {points.map((point) => {
            const selected = String(point.id) === String(selectedId);
            return (
              <CircleMarker
                key={point.id}
                center={[point.latitude, point.longitude]}
                radius={selected ? 10 : 8}
                pathOptions={{
                  color: selected ? "#102a43" : "#ffffff",
                  weight: selected ? 4 : 2,
                  fillColor: COLORS[point.status] || "#2563eb",
                  fillOpacity: 1,
                }}
                eventHandlers={{ click: () => onSelect?.(point.id) }}
              >
                <Popup>
                  <strong>{point.name}</strong><br />
                  {point.status}
                  {point.confidence ? `, ${point.confidence} confidence` : ""}
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>

      <div className="map-text-alternative" aria-label={`${label} text alternative`}>
        <strong>Map locations</strong>
        {points.length ? (
          <ul>{points.map((point) => (
            <li key={point.id}>
              <button
                type="button"
                aria-pressed={String(point.id) === String(selectedId)}
                onClick={() => onSelect?.(point.id)}
              >
                {point.name} — {point.status}
                {point.confidence ? `, ${point.confidence} confidence` : ""}
              </button>
            </li>
          ))}</ul>
        ) : <p>No locations to show.</p>}
      </div>
    </div>
  );
}
