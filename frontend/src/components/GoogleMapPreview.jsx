"use client";

import { useCallback, useRef, useState } from "react";
import ExpandedMapModal from "./ExpandedMapModal.jsx";
import MapCanvas from "./MapCanvas.jsx";
import RouteLegend from "./RouteLegend.jsx";
import SensoryIndicator from "./SensoryIndicator.jsx";

function recommendationPoints(route) {
  if (!route) return [];
  const points = [];
  if (route.threshold_exceeded === false) points.push("Matches your crowd tolerance");
  if (route.sensor_coverage_ratio > 0) points.push(`${Math.round(route.sensor_coverage_ratio * 100)}% crowd-data coverage`);
  const high = (route.route_segments || []).filter((segment) => segment.congestion_level === "high").length;
  points.push(high ? `Includes ${high} high-crowd section${high === 1 ? "" : "s"}` : "Avoids known high-crowd sections");
  return points.slice(0, 4);
}

export default function GoogleMapPreview({ routes = [], selectedRouteIdentifier, onSelectRoute }) {
  const [expanded, setExpanded] = useState(false);
  const [activeView, setActiveView] = useState("map");
  const expandButtonRef = useRef(null);
  const selectedRoute = routes.find((route) => route.route_identifier === selectedRouteIdentifier);
  const openExpandedMap = useCallback(() => setExpanded(true), []);
  const closeExpandedMap = useCallback(() => setExpanded(false), []);

  return (
    <section className="map-preview glass-panel" aria-labelledby="map-preview-title">
      <h2 className="sr-only" id="map-preview-title">Map and details</h2>
      <p className="sr-only" aria-live="polite">{selectedRoute ? `${selectedRoute.route_identifier} selected` : "Select a route to compare"}</p>
      <div className="map-preview__toolbar">
        <RouteLegend />
        <div className="map-preview__actions"><div className="map-detail-tabs" role="tablist" aria-label="Route map and details"><button type="button" role="tab" aria-selected={activeView === "map"} onClick={() => setActiveView("map")}>Map</button><button type="button" role="tab" aria-selected={activeView === "details"} onClick={() => setActiveView("details")}>Details</button></div><button className="icon-button" type="button" onClick={openExpandedMap} ref={expandButtonRef} aria-label="Expand route map"><span aria-hidden="true">↗</span></button></div>
      </div>
      <div role="tabpanel" hidden={activeView !== "map"}>
        <div className="map-preview__interactive" aria-label="Open expanded route map" onClick={openExpandedMap}><MapCanvas routes={routes} selectedRouteIdentifier={selectedRouteIdentifier} onSelectRoute={onSelectRoute} /><span className="map-preview__hint">Expand map</span></div>
        {routes.length ? <div className="map-route-selector" aria-label="Map route selector">{routes.slice(0, 3).map((route, index) => <button type="button" key={`${route.route_identifier}-${index}`} className={route.route_identifier === selectedRouteIdentifier ? "map-route-selector__button--active" : ""} onClick={() => onSelectRoute?.(route.route_identifier)}>Route {index + 1}{route.is_recommended ? " · Recommended" : ""}</button>)}</div> : null}
      </div>
      <div className="route-detail-view" role="tabpanel" hidden={activeView !== "details"}>{selectedRoute ? <><div className="route-detail-view__headline"><div><h3>{selectedRoute.route_identifier}</h3><p>{selectedRoute.estimated_travel_minutes} min · {selectedRoute.travel_mode === "transit" ? "Public transport" : "Walking"}</p></div><SensoryIndicator indicator={selectedRoute.sensory_indicator} /></div><p>{selectedRoute.threshold_exceeded ? "Crowd level is above your tolerance." : "Crowd level is within your tolerance."}</p><section className="route-reasoning" aria-labelledby="route-reasoning-title"><h3 id="route-reasoning-title">Why this route is recommended</h3><ul>{recommendationPoints(selectedRoute).map((point) => <li key={point}>{point}</li>)}</ul></section></> : <p>Select a route to see its details.</p>}</div>
      <ExpandedMapModal open={expanded} onClose={closeExpandedMap} routes={routes} selectedRouteIdentifier={selectedRouteIdentifier} onSelectRoute={onSelectRoute} returnFocusRef={expandButtonRef} />
    </section>
  );
}
