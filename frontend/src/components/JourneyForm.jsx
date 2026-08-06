"use client";

import { useMemo, useState } from "react";

import TravelModeSelector from "./TravelModeSelector.jsx";

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

function buildRequest(originId, destinationId, travelMode, crowdThreshold) {
  const origin = CBD_LOCATIONS.find((location) => location.id === originId);
  const destination = CBD_LOCATIONS.find((location) => location.id === destinationId);

  return {
    origin_latitude: origin.latitude,
    origin_longitude: origin.longitude,
    destination_latitude: destination.latitude,
    destination_longitude: destination.longitude,
    travel_mode: travelMode,
    preferred_crowd_threshold: Number(crowdThreshold),
  };
}

function validate(originId, destinationId, travelMode, crowdThreshold) {
  const errors = {};
  if (!originId) errors.origin = "Choose an origin.";
  if (!destinationId) errors.destination = "Choose a destination.";
  if (originId && destinationId && originId === destinationId) {
    errors.destination = "Choose a destination different from the origin.";
  }
  if (!["walking", "transit"].includes(travelMode)) {
    errors.travelMode = "Choose walking or public transport.";
  }
  const numericThreshold = Number(crowdThreshold);
  if (!Number.isInteger(numericThreshold) || numericThreshold < 1 || numericThreshold > 5) {
    errors.crowdThreshold = "Choose a crowd tolerance from 1 to 5.";
  }
  return errors;
}

export default function JourneyForm({ onSubmit, loading }) {
  const [originId, setOriginId] = useState("bourke-street-mall");
  const [destinationId, setDestinationId] = useState("flinders-street");
  const [travelMode, setTravelMode] = useState("walking");
  const [crowdThreshold, setCrowdThreshold] = useState(3);
  const [submitted, setSubmitted] = useState(false);

  const errors = useMemo(
    () => validate(originId, destinationId, travelMode, crowdThreshold),
    [originId, destinationId, travelMode, crowdThreshold],
  );
  const hasErrors = Object.keys(errors).length > 0;

  function handleSubmit(event) {
    event.preventDefault();
    setSubmitted(true);
    if (hasErrors) return;
    onSubmit(buildRequest(originId, destinationId, travelMode, crowdThreshold));
  }

  const showErrors = submitted && hasErrors;

  return (
    <form className="journey-form" id="journey-form" onSubmit={handleSubmit} noValidate aria-label="Journey planner">
      <div className="field-grid">
        <label className="form-field">
          <span>Origin</span>
          <select
            value={originId}
            onChange={(event) => setOriginId(event.target.value)}
            disabled={loading}
            aria-invalid={Boolean(showErrors && errors.origin)}
            aria-describedby={showErrors && errors.origin ? "origin-error" : undefined}
          >
            <option value="">Select origin</option>
            {CBD_LOCATIONS.map((location) => (
              <option key={location.id} value={location.id}>
                {location.label}
              </option>
            ))}
          </select>
          {showErrors && errors.origin ? <strong className="field-error" id="origin-error">{errors.origin}</strong> : null}
        </label>

        <label className="form-field">
          <span>Destination</span>
          <select
            value={destinationId}
            onChange={(event) => setDestinationId(event.target.value)}
            disabled={loading}
            aria-invalid={Boolean(showErrors && errors.destination)}
            aria-describedby={showErrors && errors.destination ? "destination-error" : undefined}
          >
            <option value="">Select destination</option>
            {CBD_LOCATIONS.map((location) => (
              <option key={location.id} value={location.id}>
                {location.label}
              </option>
            ))}
          </select>
          {showErrors && errors.destination ? <strong className="field-error" id="destination-error">{errors.destination}</strong> : null}
        </label>

        <TravelModeSelector
          value={travelMode}
          onChange={setTravelMode}
          disabled={loading}
          error={showErrors ? errors.travelMode : undefined}
        />

        <label className="form-field form-field--threshold">
          <span>Crowd tolerance</span>
          <select
            value={crowdThreshold}
            onChange={(event) => setCrowdThreshold(Number(event.target.value))}
            disabled={loading}
            aria-invalid={Boolean(showErrors && errors.crowdThreshold)}
            aria-describedby="crowd-threshold-help"
          >
            <option value={1}>1 - Very low tolerance</option>
            <option value={2}>2 - Low tolerance</option>
            <option value={3}>3 - Moderate tolerance</option>
            <option value={4}>4 - Higher tolerance</option>
            <option value={5}>5 - Highest tolerance</option>
          </select>
          <small id="crowd-threshold-help">Lower levels prefer calmer corridors. The backend applies the exact score limit.</small>
          {showErrors && errors.crowdThreshold ? <strong className="field-error">{errors.crowdThreshold}</strong> : null}
        </label>
      </div>

      <button className="primary-button" type="submit" disabled={loading}>
        {loading ? "Finding routes…" : "Find routes"}
      </button>
      <div className="sr-only" aria-live="assertive">
        {showErrors ? Object.values(errors).join(" ") : ""}
      </div>
    </form>
  );
}
