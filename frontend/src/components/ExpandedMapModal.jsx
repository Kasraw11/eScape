"use client";

import { useEffect, useRef } from "react";

import MapCanvas from "./MapCanvas.jsx";
import RouteLegend from "./RouteLegend.jsx";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export default function ExpandedMapModal({ open, onClose, routes, selectedRouteIdentifier, onSelectRoute, returnFocusRef }) {
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);
  const selectedRoute = routes.find((route) => route.route_identifier === selectedRouteIdentifier);

  useEffect(() => {
    if (!open) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;

      const focusable = [...dialogRef.current.querySelectorAll(FOCUSABLE_SELECTOR)];
      if (!focusable.length) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      returnFocusRef?.current?.focus();
    };
  }, [onClose, open, returnFocusRef]);

  if (!open) return null;

  return (
    <div className="map-modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section
        className="map-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="expanded-map-title"
        ref={dialogRef}
        tabIndex={-1}
      >
        <header className="map-modal__header">
          <div>
            <p className="section-kicker">Expanded view</p>
            <h2 id="expanded-map-title">Route preview</h2>
            <p>
              {selectedRoute
                ? `${selectedRoute.route_identifier} · ${selectedRoute.estimated_travel_minutes} min · ${selectedRoute.travel_mode === "transit" ? "Public transport" : "Walking"}`
                : "Select a route to compare it on the map."}
            </p>
          </div>
          <button className="map-modal__close" type="button" onClick={onClose} ref={closeButtonRef} aria-label="Close expanded map">
            <span aria-hidden="true">×</span>
          </button>
        </header>

        <div className="map-modal__canvas-wrap">
          <MapCanvas
            routes={routes}
            selectedRouteIdentifier={selectedRouteIdentifier}
            onSelectRoute={onSelectRoute}
            expanded
          />
        </div>

        <footer className="map-modal__footer">
          <div className="map-route-selector" aria-label="Expanded map route selector">
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
        </footer>
      </section>
    </div>
  );
}
