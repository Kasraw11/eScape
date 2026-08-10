"use client";

import { useEffect } from "react";

import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Circle,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";

import L from "leaflet";

import "leaflet/dist/leaflet.css";


const MELBOURNE_CBD_CENTER = [
  -37.8136,
  144.9631,
];


// --------------------------------------------------
// Fit map around all returned routes
// --------------------------------------------------

function FitRouteBounds({
  routes,
  expanded,
}) {
  const map = useMap();

  const routeSignature = routes
    .map((route) => {
      const points =
        route.points || [];

      if (!points.length) {
        return "";
      }

      const first =
        points[0];

      const last =
        points[
          points.length - 1
        ];

      return [
        route.route_identifier,
        points.length,
        first?.[0],
        first?.[1],
        last?.[0],
        last?.[1],
      ].join("-");
    })
    .join("|");


  useEffect(() => {
    const points =
      routes.flatMap(
        (route) =>
          route.points || []
      );

    if (!points.length) {
      map.setView(
        MELBOURNE_CBD_CENTER,
        15,
        {
          animate: false,
        }
      );

      return;
    }

    const bounds =
      L.latLngBounds(
        points.map(
          ([lat, lng]) => [
            lat,
            lng,
          ]
        )
      );

    map.fitBounds(
      bounds,
      {
        padding:
          expanded
            ? [60, 60]
            : [30, 30],

        animate: false,
      }
    );

  }, [
    map,
    routeSignature,
    expanded,
    routes,
  ]);


  return null;
}


// --------------------------------------------------
// Full route background styling
// --------------------------------------------------

function routeStyle(
  route,
  selected
) {
  if (selected) {
    return {
      color: "#64748b",
      weight: 5,
      opacity: 0.35,
    };
  }

  if (route.is_recommended) {
    return {
      color: "#94a3b8",
      weight: 4,
      opacity: 0.25,
    };
  }

  return {
    color: "#cbd5e1",
    weight: 3,
    opacity: 0.2,
  };
}


// --------------------------------------------------
// Crowd color helper
// --------------------------------------------------

function crowdColor(level) {
  const value =
    String(
      level || ""
    ).toLowerCase();

  if (value === "low") {
    return "#22c55e";
  }

  if (
    value === "moderate" ||
    value === "medium"
  ) {
    return "#f59e0b";
  }

  if (value === "high") {
    return "#ef4444";
  }

  return "#9ca3af";
}


// --------------------------------------------------
// Sensory segment styling
// --------------------------------------------------

function segmentStyle(
  segment
) {
  return {
    color:
      crowdColor(
        segment.congestion_level
      ),

    weight: 9,

    opacity: 1,

    lineCap: "round",

    lineJoin: "round",
  };
}


// --------------------------------------------------
// Draw sensory-aware route segments
// --------------------------------------------------

function SensorySegments({
  route,
  onSelectRoute,
}) {
  const segments =
    route.route_segments || [];


  return (
    <>
      {segments.map(
        (segment) => {

          const positions =
            (
              segment.points ||
              []
            ).map(
              ([lat, lng]) => [
                lat,
                lng,
              ]
            );


          if (
            positions.length < 2
          ) {
            return null;
          }


          return (
            <Polyline
              key={
                `${route.route_identifier}-segment-` +
                `${segment.segment_sequence}`
              }

              positions={
                positions
              }

              pathOptions={
                segmentStyle(
                  segment
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
        }
      )}
    </>
  );
}


// --------------------------------------------------
// Collect unique sensors from active route
// --------------------------------------------------

function getRouteSensors(
  route
) {
  if (!route) {
    return [];
  }


  const sensors = [];

  const seenSensorIds =
    new Set();


  for (
    const segment
    of route.route_segments || []
  ) {
    for (
      const sensor
      of segment.matched_sensors || []
    ) {

      if (
        seenSensorIds.has(
          sensor.sensor_id
        )
      ) {
        continue;
      }


      seenSensorIds.add(
        sensor.sensor_id
      );


      sensors.push(
        sensor
      );
    }
  }


  return sensors;
}


// --------------------------------------------------
// Draw pedestrian sensor markers
// --------------------------------------------------

function SensorMarkers({
  route,
}) {
  const sensors =
    getRouteSensors(
      route
    );


  return (
    <>
      {sensors.map(
        (sensor) => {

          const color =
            crowdColor(
              sensor.congestion_level
            );


          return (
            <CircleMarker
              key={
                `sensor-${sensor.sensor_id}`
              }

              center={[
                sensor.latitude,
                sensor.longitude,
              ]}

              radius={7}

              pathOptions={{
                color,

                fillColor:
                  color,

                fillOpacity:
                  0.85,

                weight: 2,
              }}
            >
              <Popup>
                <div>
                  <strong>
                    {
                      sensor.sensor_name ||
                      `Sensor ${sensor.sensor_id}`
                    }
                  </strong>

                  <br />

                  Pedestrian count:
                  {" "}
                  {
                    sensor.pedestrian_count ??
                    "Unavailable"
                  }

                  <br />

                  Crowd level:
                  {" "}
                  {
                    sensor.congestion_level ||
                    "Unavailable"
                  }
                </div>
              </Popup>
            </CircleMarker>
          );
        }
      )}
    </>
  );
}


// --------------------------------------------------
// Draw Moderate / High crowd hotspot areas
// --------------------------------------------------

function SensorHotspots({
  route,
}) {
  const sensors =
    getRouteSensors(route);

  return (
    <>
      {sensors.map((sensor) => {
        const level = String(
          sensor.congestion_level || ""
        ).toLowerCase();

        // Only show larger hotspot areas
        // for Moderate and High crowding.
        if (
          level !== "moderate" &&
          level !== "medium" &&
          level !== "high"
        ) {
          return null;
        }

        const color =
          crowdColor(
            sensor.congestion_level
          );

        const radius =
          level === "high"
            ? 120
            : 80;

        return (
          <Circle
            key={
              `hotspot-${sensor.sensor_id}`
            }

            center={[
              sensor.latitude,
              sensor.longitude,
            ]}

            radius={radius}

            interactive={false}

            pathOptions={{
              color,

              fillColor:
                color,

              fillOpacity:
                level === "high"
                  ? 0.18
                  : 0.12,

              opacity: 0.35,

              weight: 1,
            }}
          />
        );
      })}
    </>
  );
}



// --------------------------------------------------
// Public transport helpers
// --------------------------------------------------

function transportEmoji(
  mode
) {
  const value =
    String(
      mode || ""
    ).toLowerCase();

  if (value === "train") {
    return "🚆";
  }

  if (value === "tram") {
    return "🚋";
  }

  if (value === "bus") {
    return "🚌";
  }

  return "🚏";
}


function transportLabel(
  mode
) {
  const value =
    String(
      mode || ""
    ).toLowerCase();

  if (value === "train") {
    return "Train";
  }

  if (value === "tram") {
    return "Tram";
  }

  if (value === "bus") {
    return "Bus";
  }

  return "Public transport";
}

function distanceBetweenStopsMeters(
  stopA,
  stopB
) {
  const earthRadius = 6371000;

  const lat1 =
    stopA.latitude *
    Math.PI / 180;

  const lat2 =
    stopB.latitude *
    Math.PI / 180;

  const deltaLat =
    (
      stopB.latitude -
      stopA.latitude
    ) *
    Math.PI / 180;

  const deltaLng =
    (
      stopB.longitude -
      stopA.longitude
    ) *
    Math.PI / 180;

  const a =
    Math.sin(
      deltaLat / 2
    ) ** 2 +
    Math.cos(lat1) *
    Math.cos(lat2) *
    Math.sin(
      deltaLng / 2
    ) ** 2;

  const c =
    2 *
    Math.atan2(
      Math.sqrt(a),
      Math.sqrt(1 - a)
    );

  return (
    earthRadius * c
  );
}


function getVisibleTransportStops(
  route
) {
  const stops =
    route?.transport_stops || [];

  const limits = {
    train: 3,
    tram: 6,
    bus: 3,
  };

  const minimumSpacing = {
    train: 70,
    tram: 70,
    bus: 70,
  };

  const grouped = {
    train: [],
    tram: [],
    bus: [],
  };

  for (const stop of stops) {
    const mode =
      String(
        stop.mode || ""
      ).toLowerCase();

    if (!grouped[mode]) {
      continue;
    }

    grouped[mode].push(
      stop
    );
  }


  const selectedStops = [];


  for (
    const mode
    of Object.keys(grouped)
  ) {

    // Prefer stops closest
    // to the walking route.
    const candidates =
      [...grouped[mode]]
        .sort(
          (a, b) =>
            (
              a.distance_m ??
              Infinity
            ) -
            (
              b.distance_m ??
              Infinity
            )
        );


    const kept = [];


    for (
      const candidate
      of candidates
    ) {

      const tooClose =
        kept.some(
          (existing) =>
            distanceBetweenStopsMeters(
              candidate,
              existing
            ) <
            minimumSpacing[mode]
        );


      if (tooClose) {
        continue;
      }


      kept.push(
        candidate
      );


      if (
        kept.length >=
        limits[mode]
      ) {
        break;
      }
    }


    selectedStops.push(
      ...kept
    );
  }


  // Display them in the order
  // they appear along the route.
  return selectedStops.sort(
    (a, b) =>
      (
        a.stop_sequence ??
        9999
      ) -
      (
        b.stop_sequence ??
        9999
      )
  );
}

// --------------------------------------------------
// Draw public transport access points
// --------------------------------------------------

function TransportStopMarkers({
  route,
}) {
  const stops =
    getVisibleTransportStops(
      route
    );


  return (
    <>
      {stops.map(
        (stop) => {

          if (
            stop.latitude == null ||
            stop.longitude == null
          ) {
            return null;
          }


          const icon =
            L.divIcon({
              className:
                "escape-transport-stop-marker",

              html: `
                <div
                  style="
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: white;
                    border: 2px solid #334155;
                    border-radius: 50%;
                    font-size: 16px;
                    line-height: 1;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
                  "
                >
                  ${transportEmoji(
                    stop.mode
                  )}
                </div>
              `,

              iconSize: [
                30,
                30,
              ],

              iconAnchor: [
                15,
                15,
              ],

              popupAnchor: [
                0,
                -16,
              ],
            });


          return (
            <Marker
              key={
                `transport-${stop.stop_id}`
              }

              position={[
                stop.latitude,
                stop.longitude,
              ]}

              icon={
                icon
              }
            >
              <Popup>
                <div>
                  <strong>
                    {
                      stop.stop_name
                    }
                  </strong>

                  <br />

                  {
                    transportEmoji(
                      stop.mode
                    )
                  }
                  {" "}
                  {
                    transportLabel(
                      stop.mode
                    )
                  }

                  <br />

                  Distance from route:
                  {" "}
                  {
                    stop.distance_m ??
                    "Unknown"
                  }
                  {
                    stop.distance_m != null
                      ? " m"
                      : ""
                  }
                </div>
              </Popup>
            </Marker>
          );
        }
      )}
    </>
  );
}


// --------------------------------------------------
// Main map
// --------------------------------------------------

export default function MapCanvas({
  routes = [],
  selectedRouteIdentifier,
  onSelectRoute,
  expanded = false,
}) {

  // Selected route first.
  // Otherwise recommended.
  // Otherwise first route.
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
        position:
          "relative",

        width:
          "100%",

        height:
          expanded
            ? "70vh"
            : "100%",

        minHeight:
          expanded
            ? "70vh"
            : "400px",

        overflow:
          "hidden",

        borderRadius:
          "14px",
      }}
    >

      <MapContainer
        center={
          MELBOURNE_CBD_CENTER
        }

        zoom={15}

        scrollWheelZoom={
          true
        }

        style={{
          width:
            "100%",

          height:
            "100%",
        }}
      >

        <TileLayer
          attribution="&copy; OpenStreetMap contributors"

          url={
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          }

          updateWhenZooming={
            false
          }

          keepBuffer={2}
        />


        <FitRouteBounds
          routes={
            routes
          }

          expanded={
            expanded
          }
        />


        {/* ----------------------------------------
            Full routes underneath
        ----------------------------------------- */}

        {routes.map(
          (route) => {

            const selected =
              route.route_identifier ===
              activeRoute
                ?.route_identifier;


            const positions =
              (
                route.points ||
                []
              ).map(
                ([lat, lng]) => [
                  lat,
                  lng,
                ]
              );


            if (
              positions.length < 2
            ) {
              return null;
            }


            return (
              <Polyline
                key={
                  route.route_identifier
                }

                positions={
                  positions
                }

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
          }
        )}


        {/* ----------------------------------------
            Hotspot areas
        ----------------------------------------- */}

        {activeRoute && (
          <SensorHotspots
            route={
              activeRoute
            }
          />
        )}


        {/* ----------------------------------------
            Sensory route segments
        ----------------------------------------- */}

        {activeRoute && (
          <SensorySegments
            route={
              activeRoute
            }

            onSelectRoute={
              onSelectRoute
            }
          />
        )}


        {/* ----------------------------------------
            Pedestrian sensor dots
        ----------------------------------------- */}

        {activeRoute && (
          <SensorMarkers
            route={
              activeRoute
            }
          />
        )}


        {/* ----------------------------------------
            Public transport access points
        ----------------------------------------- */}

        {activeRoute && (
          <TransportStopMarkers
            route={
              activeRoute
            }
          />
        )}

      </MapContainer>


      {/* ------------------------------------------
          Map legend
      ------------------------------------------- */}

      <div
        style={{
          position:
            "absolute",

          bottom:
            "16px",

          left:
            "16px",

          background:
            "white",

          padding:
            "10px 12px",

          borderRadius:
            "10px",

          boxShadow:
            "0 2px 8px rgba(0,0,0,0.15)",

          fontSize:
            "12px",

          zIndex:
            1000,
        }}
      >

        <div>
          <span
            style={{
              color:
                "#22c55e",
            }}
          >
            ●
          </span>

          {" "}
          Low crowd
        </div>


        <div>
          <span
            style={{
              color:
                "#f59e0b",
            }}
          >
            ●
          </span>

          {" "}
          Moderate crowd
        </div>


        <div>
          <span
            style={{
              color:
                "#ef4444",
            }}
          >
            ●
          </span>

          {" "}
          High crowd
        </div>


        <div>
          <span
            style={{
              color:
                "#9ca3af",
            }}
          >
            ●
          </span>

          {" "}
          No data
        </div>


        <div
          style={{
            marginTop:
              "6px",

            paddingTop:
              "6px",

            borderTop:
              "1px solid #e2e8f0",
          }}
        >
          🚆 Train
        </div>

        <div>
          🚋 Tram
        </div>

        <div>
          🚌 Bus
        </div>

      </div>

    </div>
  );
}