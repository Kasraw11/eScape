"use client";

import { useEffect, useRef, useState } from "react";

import {
  hasConfiguredMapsKey,
  loadGoogleMaps,
  MELBOURNE_CBD_CENTER,
  MISSING_MAPS_KEY_MESSAGE,
} from "../services/googleMapsLoader.js";

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

export default function PointMap({ points, selectedId, onSelect, onChooseLocation, expanded = false, label = "Melbourne map" }) {
  const containerRef = useRef(null);
  const [loadError, setLoadError] = useState("");
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
  const configured = hasConfiguredMapsKey(apiKey);

  useEffect(() => {
    if (!configured || !containerRef.current) return undefined;
    let cancelled = false;
    const markers = [];
    let mapClickListener;
    loadGoogleMaps(apiKey).then((maps) => {
      if (cancelled || !containerRef.current) return;
      const center = points[0] ? { lat: points[0].latitude, lng: points[0].longitude } : MELBOURNE_CBD_CENTER;
      const map = new maps.Map(containerRef.current, {
        center,
        zoom: 14,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
      });
      const bounds = new maps.LatLngBounds();
      points.forEach((point) => {
        const selected = String(point.id) === String(selectedId);
        const marker = new maps.Marker({
          map,
          position: { lat: point.latitude, lng: point.longitude },
          title: `${point.name}: ${point.status}`,
          icon: maps.SymbolPath ? {
            path: maps.SymbolPath.CIRCLE,
            fillColor: COLORS[point.status] || "#2563eb",
            fillOpacity: 1,
            strokeColor: selected ? "#102a43" : "#ffffff",
            strokeWeight: selected ? 4 : 2,
            scale: selected ? 10 : 8,
          } : undefined,
        });
        marker.addListener("click", () => onSelect?.(point.id));
        markers.push(marker);
        bounds.extend({ lat: point.latitude, lng: point.longitude });
      });
      if (points.length > 1) map.fitBounds(bounds, expanded ? 60 : 36);
      mapClickListener = onChooseLocation ? map.addListener("click", (event) => {
        const latitude = event.latLng?.lat?.();
        const longitude = event.latLng?.lng?.();
        if (Number.isFinite(latitude) && Number.isFinite(longitude)) onChooseLocation({ latitude, longitude, label: "Selected map location" });
      }) : null;
    }).catch(() => {
      if (!cancelled) setLoadError("Map preview could not load. The text list remains available.");
    });
    return () => {
      cancelled = true;
      markers.forEach((marker) => marker.setMap?.(null));
      mapClickListener?.remove?.();
    };
  }, [apiKey, configured, expanded, onChooseLocation, onSelect, points, selectedId]);

  return (
    <div className="point-map">
      {configured ? <div className="map-canvas" ref={containerRef} aria-label={label} /> : <p className="map-notice">{MISSING_MAPS_KEY_MESSAGE}</p>}
      {loadError ? <p className="map-notice" role="alert">{loadError}</p> : null}
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
