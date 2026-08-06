"use client";

import { useEffect, useRef, useState } from "react";
import {
  hasConfiguredMapsKey,
  loadGoogleMaps,
  MELBOURNE_CBD_CENTER,
  MISSING_MAPS_KEY_MESSAGE,
} from "../services/googleMapsLoader.js";

export { hasConfiguredMapsKey, MISSING_MAPS_KEY_MESSAGE } from "../services/googleMapsLoader.js";

function decodePolyline(polyline) {
  if (!polyline) return [];

  const points = [];
  let index = 0;
  let latitude = 0;
  let longitude = 0;

  while (index < polyline.length) {
    let result = 1;
    let shift = 0;
    let byte;
    do {
      byte = polyline.charCodeAt(index) - 64;
      index += 1;
      result += byte << shift;
      shift += 5;
    } while (byte >= 31);
    latitude += result & 1 ? ~(result >> 1) : result >> 1;

    result = 1;
    shift = 0;
    do {
      byte = polyline.charCodeAt(index) - 64;
      index += 1;
      result += byte << shift;
      shift += 5;
    } while (byte >= 31);
    longitude += result & 1 ? ~(result >> 1) : result >> 1;

    points.push({ lat: latitude * 1e-5, lng: longitude * 1e-5 });
  }

  return points;
}

function routePath(route) {
  const overviewPath = decodePolyline(route.encoded_polyline);
  if (overviewPath.length) return overviewPath;
  return (route.route_segments || []).flatMap((segment) => decodePolyline(segment.encoded_polyline));
}

function routeStyle(route, selected) {
  const indicator = (route.sensory_indicator || "unavailable").toLowerCase();
  const unavailable = indicator === "unavailable";
  const high = indicator === "high" || indicator === "medium";

  return {
    strokeColor: unavailable ? "#64748b" : high ? "#dc2626" : "#15803d",
    strokeOpacity: unavailable ? 0 : selected ? 0.98 : 0.58,
    strokeWeight: selected ? 7 : 4,
    zIndex: selected ? 3 : route.is_recommended ? 2 : 1,
    icons: unavailable
      ? [{ icon: { path: "M 0,-1 0,1", strokeOpacity: selected ? 0.95 : 0.65, scale: 3 }, offset: "0", repeat: "14px" }]
      : undefined,
  };
}

function segmentStyle(segment, route, selected) {
  const level = (segment.congestion_level || "unavailable").toLowerCase();
  const unavailable = level === "unavailable" || segment.data_availability === "unavailable";
  const high = level === "high";
  return {
    strokeColor: unavailable ? "#64748b" : high ? "#dc2626" : "#15803d",
    strokeOpacity: unavailable ? 0 : selected ? 0.98 : 0.64,
    strokeWeight: selected ? 7 : route.is_recommended ? 5 : 4,
    zIndex: selected ? 4 : route.is_recommended ? 3 : 2,
    icons: unavailable
      ? [{ icon: { path: "M 0,-1 0,1", strokeOpacity: selected ? 0.95 : 0.68, scale: 3 }, offset: "0", repeat: "14px" }]
      : undefined,
  };
}

function drawableSections(route) {
  const segments = (route.route_segments || [])
    .map((segment) => ({ segment, path: decodePolyline(segment.encoded_polyline) }))
    .filter(({ path }) => path.length > 0);
  if (segments.length) return segments;
  const path = routePath(route);
  return path.length ? [{ segment: null, path }] : [];
}

export default function MapCanvas({ routes = [], selectedRouteIdentifier, onSelectRoute, expanded = false }) {
  const mapRef = useRef(null);
  const [loadError, setLoadError] = useState("");
  const mapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
  const configured = hasConfiguredMapsKey(mapsApiKey);

  useEffect(() => {
    if (!configured || !mapRef.current) return undefined;

    let cancelled = false;
    const polylines = [];
    setLoadError("");

    loadGoogleMaps(mapsApiKey)
      .then((maps) => {
        if (cancelled || !mapRef.current) return;
        const map = new maps.Map(mapRef.current, {
          center: MELBOURNE_CBD_CENTER,
          zoom: 15,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
          zoomControl: true,
        });
        const bounds = new maps.LatLngBounds();
        const routePolylines = routes.flatMap((route) => (
          drawableSections(route).map(({ segment, path }) => ({ route, segment, path }))
        ));

        if (!routePolylines.length) {
          new maps.Marker({ map, position: MELBOURNE_CBD_CENTER, title: "Melbourne CBD" });
          return;
        }

        routePolylines.forEach(({ route, segment, path }) => {
          const selected = route.route_identifier === selectedRouteIdentifier;
          path.forEach((point) => bounds.extend(point));
          const style = segment ? segmentStyle(segment, route, selected) : routeStyle(route, selected);
          const polyline = new maps.Polyline({ map, path, ...style });
          polyline.addListener("click", () => onSelectRoute?.(route.route_identifier));
          polylines.push(polyline);
        });
        map.fitBounds(bounds, expanded ? 56 : 32);
      })
      .catch(() => {
        if (!cancelled) setLoadError("Map preview could not load. Check the browser key and Google Maps configuration.");
      });

    return () => {
      cancelled = true;
      polylines.forEach((polyline) => polyline.setMap?.(null));
    };
  }, [configured, expanded, mapsApiKey, onSelectRoute, routes, selectedRouteIdentifier]);

  if (!configured) return <p className="map-notice">{MISSING_MAPS_KEY_MESSAGE}</p>;

  return (
    <>
      <div className="map-canvas" ref={mapRef} aria-label={expanded ? "Expanded Melbourne CBD route map" : "Melbourne CBD route map"} />
      {loadError ? <p className="map-notice" role="alert">{loadError}</p> : null}
    </>
  );
}
