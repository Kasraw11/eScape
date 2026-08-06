"use client";

import { useMemo, useState } from "react";
import LocationInput from "./LocationInput.jsx";
import TravelModeSelector from "./TravelModeSelector.jsx";

export const CBD_LOCATIONS = [
  { id: "bourke-street-mall", label: "Bourke Street Mall", formattedAddress: "Bourke Street Mall, Melbourne VIC", latitude: -37.81362, longitude: 144.96307 },
  { id: "flinders-street", label: "Flinders Street Station", formattedAddress: "Flinders Street Station, Melbourne VIC", latitude: -37.81827, longitude: 144.96706 },
  { id: "flagstaff-gardens", label: "Flagstaff Gardens", formattedAddress: "Flagstaff Gardens, Melbourne VIC", latitude: -37.81007, longitude: 144.95577 },
  { id: "state-library", label: "State Library Victoria", formattedAddress: "328 Swanston Street, Melbourne VIC", latitude: -37.80981, longitude: 144.96519 },
];

function insideSupportedCbd(place) { return place && place.latitude >= -37.829 && place.latitude <= -37.795 && place.longitude >= 144.936 && place.longitude <= 144.991; }

export default function JourneyForm({ onSubmit, loading }) {
  const [originText, setOriginText] = useState(CBD_LOCATIONS[0].label);
  const [destinationText, setDestinationText] = useState(CBD_LOCATIONS[1].label);
  const [origin, setOrigin] = useState(CBD_LOCATIONS[0]);
  const [destination, setDestination] = useState(CBD_LOCATIONS[1]);
  const [travelMode, setTravelMode] = useState("walking");
  const [crowdThreshold, setCrowdThreshold] = useState(3);
  const [submitted, setSubmitted] = useState(false);
  const [locationNotice, setLocationNotice] = useState("");

  const errors = useMemo(() => {
    const next = {};
    if (!originText.trim()) next.origin = "Enter a starting location."; else if (!origin) next.origin = "Select a valid location from the suggestions.";
    if (!destinationText.trim()) next.destination = "Enter a destination."; else if (!destination) next.destination = "Select a valid location from the suggestions.";
    if (origin && destination && origin.latitude === destination.latitude && origin.longitude === destination.longitude) next.destination = "Origin and destination cannot be the same.";
    else if (destination && !insideSupportedCbd(destination)) next.destination = "Destination must be within Melbourne CBD.";
    if (!["walking", "transit"].includes(travelMode)) next.travelMode = "Select a valid travel mode.";
    if (!Number.isInteger(Number(crowdThreshold)) || Number(crowdThreshold) < 1 || Number(crowdThreshold) > 5) next.crowdThreshold = "Choose a crowd tolerance from 1 to 5.";
    return next;
  }, [crowdThreshold, destination, destinationText, origin, originText, travelMode]);

  function useCurrentLocation() {
    setLocationNotice("Your location is used only to set the journey origin.");
    if (!globalThis.navigator?.geolocation) { setLocationNotice("Current location is unavailable. Enter an origin manually."); return; }
    globalThis.navigator.geolocation.getCurrentPosition((position) => {
      const place = { id: "current", label: "Current location", formattedAddress: "Current location", latitude: position.coords.latitude, longitude: position.coords.longitude };
      setOrigin(place); setOriginText(place.label); setLocationNotice("Current location selected as origin.");
    }, (error) => setLocationNotice(error.code === error.PERMISSION_DENIED ? "Location permission was denied. Enter an origin manually." : error.code === error.TIMEOUT ? "Location lookup timed out. Enter an origin manually." : "Current location is unavailable. Enter an origin manually."), { timeout: 10000, maximumAge: 120000 });
  }

  function submit(event) {
    event.preventDefault(); setSubmitted(true);
    if (Object.keys(errors).length) return;
    onSubmit({ origin_latitude: origin.latitude, origin_longitude: origin.longitude, destination_latitude: destination.latitude, destination_longitude: destination.longitude, travel_mode: travelMode, preferred_crowd_threshold: Number(crowdThreshold) }, { origin, destination, travelMode, crowdThreshold: Number(crowdThreshold) });
  }

  return <form className="journey-form" onSubmit={submit} noValidate aria-label="Journey planner"><div className="field-grid">
    <LocationInput label="Origin" value={originText} placeholder="Enter starting location" suggestions={CBD_LOCATIONS} selectedPlace={origin} loading={loading} error={submitted ? errors.origin : ""} showCurrentLocation onChange={(value) => { setOriginText(value); setOrigin(null); }} onSelectSuggestion={(place) => { setOrigin(place); setOriginText(place.label); }} onClear={() => { setOrigin(null); setOriginText(""); }} onUseCurrentLocation={useCurrentLocation} />
    <LocationInput label="Destination" value={destinationText} placeholder="Enter destination" suggestions={CBD_LOCATIONS} selectedPlace={destination} loading={loading} error={submitted ? errors.destination : ""} onChange={(value) => { setDestinationText(value); setDestination(null); }} onSelectSuggestion={(place) => { setDestination(place); setDestinationText(place.label); }} onClear={() => { setDestination(null); setDestinationText(""); }} />
    <TravelModeSelector value={travelMode} onChange={setTravelMode} disabled={loading} error={submitted ? errors.travelMode : undefined} />
    <label className="form-field form-field--threshold"><span>Crowd tolerance</span><select value={crowdThreshold} onChange={(event) => setCrowdThreshold(Number(event.target.value))} disabled={loading} aria-describedby="crowd-threshold-help"><option value={1}>1 - Very low tolerance</option><option value={2}>2 - Low tolerance</option><option value={3}>3 - Moderate tolerance</option><option value={4}>4 - Higher tolerance</option><option value={5}>5 - Highest tolerance</option></select><small id="crowd-threshold-help">Lower levels prefer calmer corridors. The backend applies the exact score limit.</small>{submitted && errors.crowdThreshold ? <strong className="field-error">{errors.crowdThreshold}</strong> : null}</label>
  </div>{locationNotice ? <p className="field-notice" role="status">{locationNotice}</p> : null}<button className="primary-button" type="submit" disabled={loading}>{loading ? "Finding calmer routes…" : "Find calmer routes"}</button><div className="sr-only" aria-live="assertive">{submitted ? Object.values(errors).join(" ") : ""}</div></form>;
}
