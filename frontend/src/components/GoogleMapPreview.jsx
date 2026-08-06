"use client";

import { useEffect, useRef, useState } from "react";

const placeholderKey = "PASTE_YOUR_GOOGLE_MAPS_BROWSER_KEY_HERE";
const missingKeyMessage = "Map preview is unavailable until `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY` is configured.";
const melbourneCbdCenter = { lat: -37.8136, lng: 144.9631 };

function hasConfiguredMapsKey(key) {
  return Boolean(key && key.trim() && key !== placeholderKey);
}

function loadGoogleMaps(apiKey) {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return Promise.reject(new Error("Google Maps is only available in the browser."));
  }

  if (window.google?.maps) {
    return Promise.resolve(window.google.maps);
  }

  const existingScript = document.querySelector("script[data-escape-google-maps]");
  if (existingScript) {
    return new Promise((resolve, reject) => {
      existingScript.addEventListener("load", () => {
        if (window.google?.maps) {
          resolve(window.google.maps);
        } else {
          reject(new Error("Google Maps script loaded without the maps API."));
        }
      }, { once: true });
      existingScript.addEventListener("error", reject, { once: true });
    });
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}`;
    script.async = true;
    script.defer = true;
    script.dataset.escapeGoogleMaps = "true";
    script.addEventListener("load", () => {
      if (window.google?.maps) {
        resolve(window.google.maps);
      } else {
        reject(new Error("Google Maps script loaded without the maps API."));
      }
    }, { once: true });
    script.addEventListener("error", reject, { once: true });
    document.head.appendChild(script);
  });
}

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
      byte = polyline.charCodeAt(index) - 63 - 1;
      index += 1;
      result += byte << shift;
      shift += 5;
    } while (byte >= 0x1f);
    latitude += result & 1 ? ~(result >> 1) : result >> 1;

    result = 1;
    shift = 0;
    do {
      byte = polyline.charCodeAt(index) - 63 - 1;
      index += 1;
      result += byte << shift;
      shift += 5;
    } while (byte >= 0x1f);
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

export default function GoogleMapPreview({ routes = [], selectedRouteIdentifier, onSelectRoute }) {
  const mapRef = useRef(null);
  const [loadError, setLoadError] = useState("");
  const mapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
  const configured = hasConfiguredMapsKey(mapsApiKey);

  useEffect(() => {
    if (!configured || !mapRef.current) return undefined;

    let cancelled = false;
    loadGoogleMaps(mapsApiKey)
      .then((maps) => {
        if (cancelled || !mapRef.current) return;
        const map = new maps.Map(mapRef.current, {
          center: melbourneCbdCenter,
          zoom: 15,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
        });

        const bounds = new maps.LatLngBounds();
        const routePolylines = routes
          .map((route) => ({ route, path: routePath(route) }))
          .filter(({ path }) => path.length > 0);

        if (!routePolylines.length) {
          new maps.Marker({
            map,
            position: melbourneCbdCenter,
            title: "Melbourne CBD",
          });
          return;
        }

        routePolylines.forEach(({ route, path }) => {
          const selected = route.route_identifier === selectedRouteIdentifier;
          const recommended = route.is_recommended;
          path.forEach((point) => bounds.extend(point));

          const polyline = new maps.Polyline({
            map,
            path,
            strokeColor: recommended ? "#19765d" : selected ? "#1f5fbf" : "#6f7f78",
            strokeOpacity: selected || recommended ? 0.95 : 0.55,
            strokeWeight: selected || recommended ? 6 : 4,
            zIndex: selected ? 3 : recommended ? 2 : 1,
          });

          polyline.addListener("click", () => {
            onSelectRoute?.(route.route_identifier);
          });
        });

        map.fitBounds(bounds);
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError("Map preview could not load. Check the browser key and Google Maps configuration.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [configured, routes, selectedRouteIdentifier, onSelectRoute]);

  if (!configured) {
    return <p className="map-notice">{missingKeyMessage}</p>;
  }

  return (
    <section className="map-preview" aria-label="Melbourne CBD map preview">
      <div className="map-preview__canvas" ref={mapRef} />
      {routes.length ? (
        <div className="map-route-selector" aria-label="Map route selector">
          {routes.map((route) => (
            <button
              type="button"
              key={route.route_identifier}
              className={route.route_identifier === selectedRouteIdentifier ? "map-route-selector__button--active" : ""}
              onClick={() => onSelectRoute?.(route.route_identifier)}
            >
              {route.route_identifier}
              {route.is_recommended ? " - recommended" : ""}
            </button>
          ))}
        </div>
      ) : null}
      {loadError ? <p className="map-notice" role="alert">{loadError}</p> : null}
    </section>
  );
}
