"use client";

import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  useMap,
} from "react-leaflet";

import L from "leaflet";

import "leaflet/dist/leaflet.css";


const MELBOURNE_CBD_CENTER = [
  -37.8136,
  144.9631,
];


/**
 * Automatically fits the map around all returned routes.
 */
function FitRouteBounds({
  routes,
  expanded,
}) {
  const map = useMap();

  useEffect(() => {
    const points = routes.flatMap(
      (route) => route.points || []
    );

    if (!points.length) {
      map.setView(
        MELBOURNE_CBD_CENTER,
        15
      );

      return;
    }

    const bounds = L.latLngBounds(
      points.map(
        ([lat, lng]) => [lat, lng]
      )
    );

    map.fitBounds(bounds, {
      padding: expanded
        ? [60, 60]
        : [30, 30],
    });

  }, [
    map,
    routes,
    expanded,
  ]);

  return null;
}


/**
 * Styling for the complete OSRM route.
 *
 * The full route remains underneath
 * the sensory segments.
 */
function routeStyle(
  route,
  selected
) {
  if (selected) {
    return {
      color: "#555555",
      weight: 7,
      opacity: 0.7,
    };
  }

  if (route.is_recommended) {
    return {
      color: "#777777",
      weight: 5,
      opacity: 0.5,
    };
  }

  return {
    color: "#999999",
    weight: 4,
    opacity: 0.35,
  };
}


/**
 * Styling for sensory-aware route segments.
 *
 * low      -> green
 * moderate -> orange
 * high     -> red
 * unknown  -> grey
 */
function segmentStyle(segment) {
  const level = (
    segment.congestion_level || ""
  ).toLowerCase();

  if (level === "low") {
    return {
      color: "#22c55e",
      weight: 7,
      opacity: 1,
    };
  }

  if (
    level === "moderate" ||
    level === "medium"
  ) {
    return {
      color: "#f59e0b",
      weight: 7,
      opacity: 1,
    };
  }

  if (level === "high") {
    return {
      color: "#ef4444",
      weight: 7,
      opacity: 1,
    };
  }

  return {
    color: "#9ca3af",
    weight: 7,
    opacity: 0.8,
  };
}


/**
 * Draws sensory segments
 * for one route.
 */
function SensorySegments({
  route,
  onSelectRoute,
}) {
  const segments =
    route.route_segments || [];

  return (
    <>
      {segments.map((segment) => {
        const positions = (
          segment.points || []
        ).map(
          ([lat, lng]) => [
            lat,
            lng,
          ]
        );

        if (positions.length < 2) {
          return null;
        }

        return (
          <Polyline
            key={
              `${route.route_identifier}-segment-` +
              `${segment.segment_sequence}`
            }
            positions={positions}
            pathOptions={
              segmentStyle(segment)
            }
            eventHandlers={{
              click: () =>
                onSelectRoute?.(
                  route.route_identifier
                ),
            }}
          />
        );
      })}
    </>
  );
}


/**
 * Draws OSRM walking routes using
 * OpenStreetMap + Leaflet.
 *
 * The selected route displays
 * congestion information
 * segment-by-segment.
 */
export default function MapCanvas({
  routes = [],
  selectedRouteIdentifier,
  onSelectRoute,
  expanded = false,
}) {

  /**
   * If the user selected a route,
   * use that route.
   *
   * Otherwise use the recommended route.
   *
   * Otherwise use the first route.
   */
  const activeRoute =
    routes.find(
      (route) =>
        route.route_identifier ===
        selectedRouteIdentifier
    ) ||
    routes.find(
      (route) =>
        route.is_recommended
    ) ||
    routes[0];


  return (
    <div
      className={
        expanded
          ? "map-canvas map-canvas--expanded"
          : "map-canvas"
      }
      style={{
        position: "relative",
        width: "100%",
        height: expanded
          ? "70vh"
          : "100%",
        minHeight: expanded
          ? "70vh"
          : "400px",
        overflow: "hidden",
        borderRadius: "14px",
      }}
    >

      <MapContainer
        center={
          MELBOURNE_CBD_CENTER
        }
        zoom={15}
        scrollWheelZoom={true}
        style={{
          width: "100%",
          height: "100%",
        }}
      >

        <TileLayer
          attribution={
            "&copy; OpenStreetMap contributors"
          }
          url={
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          }
        />


        <FitRouteBounds
          routes={routes}
          expanded={expanded}
        />


        {/*
          Draw complete routes first.

          These act as the background
          underneath sensory segments.
        */}
        {routes.map((route) => {
          const selected =
            route.route_identifier ===
            activeRoute?.route_identifier;

          const positions = (
            route.points || []
          ).map(
            ([lat, lng]) => [
              lat,
              lng,
            ]
          );

          if (positions.length < 2) {
            return null;
          }

          return (
            <Polyline
              key={
                route.route_identifier
              }
              positions={positions}
              pathOptions={
                routeStyle(
                  route,
                  selected
                )
              }
              eventHandlers={{
                click: () =>
                  onSelectRoute?.(
                    route.route_identifier
                  ),
              }}
            />
          );
        })}


        {/*
          Draw sensory segments
          over the active route.
        */}
        {activeRoute && (
          <SensorySegments
            route={activeRoute}
            onSelectRoute={
              onSelectRoute
            }
          />
        )}

      </MapContainer>


      {/* Sensory map legend */}
      <div
        style={{
          position: "absolute",
          bottom: "16px",
          left: "16px",
          background: "white",
          padding: "10px 12px",
          borderRadius: "10px",
          boxShadow:
            "0 2px 8px rgba(0,0,0,0.15)",
          fontSize: "12px",
          zIndex: 1000,
        }}
      >

        <div>
          <span
            style={{
              color: "#22c55e",
            }}
          >
            ●
          </span>
          {" "}Low crowd
        </div>

        <div>
          <span
            style={{
              color: "#f59e0b",
            }}
          >
            ●
          </span>
          {" "}Moderate crowd
        </div>

        <div>
          <span
            style={{
              color: "#ef4444",
            }}
          >
            ●
          </span>
          {" "}High crowd
        </div>

        <div>
          <span
            style={{
              color: "#9ca3af",
            }}
          >
            ●
          </span>
          {" "}No data
        </div>

      </div>

    </div>
  );
}