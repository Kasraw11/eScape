"use client";

import { useRef, useState } from "react";

import AccessibleMapModal from "./AccessibleMapModal.jsx";
import PointMap from "./PointMap.jsx";

export default function PointMapPanel({ title, points, selectedId, onSelect, onChooseLocation, legend, label }) {
  const [expanded, setExpanded] = useState(false);
  const expandRef = useRef(null);
  return (
    <section className="point-map-panel glass-panel" aria-labelledby="point-map-heading">
      <div className="point-map-panel__header">
        <div><p className="section-kicker">Map</p><h2 id="point-map-heading">{title}</h2></div>
        <button type="button" ref={expandRef} onClick={() => setExpanded(true)}>Expand map</button>
      </div>
      <PointMap points={points} selectedId={selectedId} onSelect={onSelect} onChooseLocation={onChooseLocation} label={label} />
      <p className="point-map-legend"><strong>Legend:</strong> {legend}</p>
      <AccessibleMapModal open={expanded} title={title} onClose={() => setExpanded(false)} returnFocusRef={expandRef}>
        <PointMap points={points} selectedId={selectedId} onSelect={onSelect} onChooseLocation={onChooseLocation} label={`Expanded ${label}`} expanded />
        <p className="point-map-legend"><strong>Legend:</strong> {legend}</p>
      </AccessibleMapModal>
    </section>
  );
}
