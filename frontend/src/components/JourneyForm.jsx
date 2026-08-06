"use client";

import { useMemo, useState } from "react";

export const CBD_LOCATIONS = [
  {
    id: "bourke-street-mall",
    label: "Bourke Street Mall",
    latitude: -37.81362,
    longitude: 144.96307,
  },
  {
    id: "flinders-street",
    label: "Flinders Street Station",
    latitude: -37.81827,
    longitude: 144.96706,
  },
  {
    id: "flagstaff-gardens",
    label: "Flagstaff Gardens",
    latitude: -37.81007,
    longitude: 144.95577,
  },
  {
    id: "state-library",
    label: "State Library Victoria",
    latitude: -37.80981,
    longitude: 144.96519,
  },
];

function buildRequest(originId, destinationId, travelMode) {
  const origin = CBD_LOCATIONS.find((location) => location.id === originId);
  const destination = CBD_LOCATIONS.find((location) => location.id === destinationId);

  return {
    origin_latitude: origin.latitude,
    origin_longitude: origin.longitude,
    destination_latitude: destination.latitude,
    destination_longitude: destination.longitude,
    travel_mode: travelMode,
  };
}

function validate(originId, destinationId, travelMode) {
  const errors = {};
  if (!originId) errors.origin = "Choose an origin.";
  if (!destinationId) errors.destination = "Choose a destination.";
  if (originId && destinationId && originId === destinationId) {
    errors.destination = "Choose a destination different from the origin.";
  }
  if (!["walking", "transit"].includes(travelMode)) {
    errors.travelMode = "Choose walking or public transport.";
  }
  return errors;
}

export default function JourneyForm({ onSubmit, loading }) {
  const [originId, setOriginId] = useState("bourke-street-mall");
  const [destinationId, setDestinationId] = useState("flinders-street");
  const [travelMode, setTravelMode] = useState("walking");
  const [submitted, setSubmitted] = useState(false);

  const errors = useMemo(() => validate(originId, destinationId, travelMode), [originId, destinationId, travelMode]);
  const hasErrors = Object.keys(errors).length > 0;

  function handleSubmit(event) {
    event.preventDefault();
    setSubmitted(true);
    if (hasErrors) return;
    onSubmit(buildRequest(originId, destinationId, travelMode));
  }

  const showErrors = submitted && hasErrors;

  return (
    <form className="journey-form" onSubmit={handleSubmit} noValidate>
      <div className="field-grid">
        <label>
          <span>Origin</span>
          <select value={originId} onChange={(event) => setOriginId(event.target.value)} disabled={loading}>
            <option value="">Select origin</option>
            {CBD_LOCATIONS.map((location) => (
              <option key={location.id} value={location.id}>
                {location.label}
              </option>
            ))}
          </select>
          {showErrors && errors.origin ? <strong className="field-error">{errors.origin}</strong> : null}
        </label>

        <label>
          <span>Destination</span>
          <select value={destinationId} onChange={(event) => setDestinationId(event.target.value)} disabled={loading}>
            <option value="">Select destination</option>
            {CBD_LOCATIONS.map((location) => (
              <option key={location.id} value={location.id}>
                {location.label}
              </option>
            ))}
          </select>
          {showErrors && errors.destination ? <strong className="field-error">{errors.destination}</strong> : null}
        </label>

        <label>
          <span>Travel mode</span>
          <select value={travelMode} onChange={(event) => setTravelMode(event.target.value)} disabled={loading}>
            <option value="walking">Walking</option>
            <option value="transit">Public transport</option>
          </select>
          {showErrors && errors.travelMode ? <strong className="field-error">{errors.travelMode}</strong> : null}
        </label>
      </div>

      <button type="submit" disabled={loading}>
        {loading ? "Generating routes..." : "Generate route alternatives"}
      </button>
    </form>
  );
}
