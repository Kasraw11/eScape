"use client";

import { useRef, useState } from "react";
import dynamic from "next/dynamic";

import AccessibleMapModal from "./AccessibleMapModal.jsx";
import AppIcon from "./app/AppIcon.jsx";

const PointMap = dynamic(() => import("./PointMap.jsx"), {
  ssr: false,
  loading: () => <p className="map-notice" role="status">Loading map…</p>,
});

export default function PointMapPanel({ title, points, selectedId, onSelect, onChooseLocation, routePoints = [], routeSegments = [], routeSummary = "", legend, label, showTextAlternative = true }) {
  const [expanded, setExpanded] = useState(false);
  const expandRef = useRef(null);
  return (
    <section className="point-map-panel glass-panel" aria-labelledby="point-map-heading">
      <div className="point-map-panel__header">
        <div><p className="section-kicker">Map</p><h2 id="point-map-heading">{title}</h2></div>
        <button type="button" ref={expandRef} onClick={() => setExpanded(true)}><AppIcon name="arrowRight" size={18} /><span>Expand map</span></button>
      </div>
      <PointMap points={points} selectedId={selectedId} onSelect={onSelect} onChooseLocation={onChooseLocation} routePoints={routePoints} routeSegments={routeSegments} label={label} showTextAlternative={showTextAlternative} />
      {routeSummary ? <p className="refuge-route-summary" role="status">{routeSummary}</p> : null}
      <p className="point-map-legend"><strong>Legend:</strong> {legend}</p>
      <AccessibleMapModal open={expanded} title={title} onClose={() => setExpanded(false)} returnFocusRef={expandRef}>
        <PointMap points={points} selectedId={selectedId} onSelect={onSelect} onChooseLocation={onChooseLocation} routePoints={routePoints} routeSegments={routeSegments} label={`Expanded ${label}`} expanded showTextAlternative={showTextAlternative} />
        <p className="point-map-legend"><strong>Legend:</strong> {legend}</p>
      </AccessibleMapModal>
    </section>
  );
}
