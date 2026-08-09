"use client";

import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import { useEffect } from "react";

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

const USER_COLOR = "#0f172a";

// AC1: the map has to centre on the user, so their position wins over the
// refuge markers. Without a location we fall back to fitting the markers,
// and with neither we just show the CBD.
function RecentreMap({ userLocation, points }) {
  const map = useMap();

  useEffect(() => {
    if (userLocation) {
      map.setView([userLocation.latitude, userLocation.longitude], 14);
      return;
    }
    if (points.length) {
      const bounds = points.map((point) => [point.latitude, point.longitude]);
      map.fitBounds(bounds, { padding: [40, 40] });
      return;
    }
    map.setView(MELBOURNE_CBD_CENTER, 14);
  }, [map, points, userLocation]);

  return null;
}

function MapClickHandler({ onChooseLocation }) {
  useMapEvents({
    click(event) {
      const { lat, lng } = event.latlng;
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        onChooseLocation?.({ latitude: lat, longitude: lng, label: "Selected map location" });
      }
    },
  });
  return null;
}

export default function PointMap({
  points = [],
  selectedId,
  onSelect,
  onChooseLocation,
  userLocation = null,
  expanded = false,
  label = "Melbourne map",
}) {
  return (
    <div className="point-map">
      {/* Height comes from the stylesheet (.map-canvas, and the refuge-page and
          modal overrides). Setting it here as well just fights those rules. */}
      <div className="map-canvas" aria-label={label}>
        <MapContainer
          center={MELBOURNE_CBD_CENTER}
          zoom={14}
          scrollWheelZoom
          style={{ width: "100%", height: "100%" }}
        >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <RecentreMap userLocation={userLocation} points={points} />
          {onChooseLocation ? <MapClickHandler onChooseLocation={onChooseLocation} /> : null}

          {userLocation ? (
            <CircleMarker
              center={[userLocation.latitude, userLocation.longitude]}
              radius={9}
              pathOptions={{ color: "#ffffff", weight: 3, fillColor: USER_COLOR, fillOpacity: 1 }}
            >
              <Tooltip direction="top">Your location</Tooltip>
            </CircleMarker>
          ) : null}

          {points.map((point) => {
            const selected = String(point.id) === String(selectedId);
            return (
              <CircleMarker
                key={point.id}
                center={[point.latitude, point.longitude]}
                radius={selected ? 11 : 8}
                pathOptions={{
                  color: selected ? "#102a43" : "#ffffff",
                  weight: selected ? 4 : 2,
                  fillColor: COLORS[point.status] || "#2563eb",
                  fillOpacity: 1,
                }}
                eventHandlers={{ click: () => onSelect?.(point.id) }}
              >
                <Tooltip direction="top">{`${point.name}: ${point.status}`}</Tooltip>
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
              <button type="button" aria-pressed={String(point.id) === String(selectedId)} onClick={() => onSelect?.(point.id)}>
                {point.name} — {point.status}{point.confidence ? `, ${point.confidence} confidence` : ""}
              </button>
            </li>
          ))}</ul>
        ) : <p>No locations to show.</p>}
      </div>
    </div>
  );
}
