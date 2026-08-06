"use client";

import { useCallback, useRef, useState } from "react";

import ExpandedMapModal from "./ExpandedMapModal.jsx";
import MapCanvas from "./MapCanvas.jsx";
import RouteLegend from "./RouteLegend.jsx";

export default function GoogleMapPreview({ routes = [], selectedRouteIdentifier, onSelectRoute }) {
  const [expanded, setExpanded] = useState(false);
  const expandButtonRef = useRef(null);
  const selectedRoute = routes.find((route) => route.route_identifier === selectedRouteIdentifier);

  const openExpandedMap = useCallback(() => {
    setExpanded(true);
  }, []);

  const closeExpandedMap = useCallback(() => {
    setExpanded(false);
  }, []);

  return (
    <section className="map-preview glass-panel" aria-labelledby="map-preview-title">
      <div className="panel-heading map-preview__heading">
        <div>
          <p className="section-kicker">Map</p>
          <h2 id="map-preview-title">Route preview</h2>
          <p>{selectedRoute ? `${selectedRoute.route_identifier} selected` : "Tap to expand map"}</p>
        </div>
        <button className="icon-button" type="button" onClick={openExpandedMap} ref={expandButtonRef} aria-label="Expand route map">
          <span aria-hidden="true">↗</span>
        </button>
      </div>

      <div
        className="map-preview__interactive"
        aria-label="Open expanded route map"
        onClick={openExpandedMap}
      >
        <MapCanvas routes={routes} selectedRouteIdentifier={selectedRouteIdentifier} onSelectRoute={onSelectRoute} />
        <span className="map-preview__hint">Tap to expand map</span>
      </div>

      {routes.length ? (
        <>
          <div className="map-route-selector" aria-label="Map route selector">
            {routes.map((route, index) => (
              <button
                type="button"
                key={`${route.route_identifier}-${index}`}
                className={route.route_identifier === selectedRouteIdentifier ? "map-route-selector__button--active" : ""}
                onClick={() => onSelectRoute?.(route.route_identifier)}
              >
                Route {index + 1}{route.is_recommended ? " · Recommended" : ""}
              </button>
            ))}
          </div>
          <RouteLegend />
        </>
      ) : null}

      <ExpandedMapModal
        open={expanded}
        onClose={closeExpandedMap}
        routes={routes}
        selectedRouteIdentifier={selectedRouteIdentifier}
        onSelectRoute={onSelectRoute}
        returnFocusRef={expandButtonRef}
      />
    </section>
  );
}
