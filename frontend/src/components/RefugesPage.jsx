"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { getRefugeDetails, planRoute, searchRefuges } from "../services/api.js";
import PointMapPanel from "./PointMapPanel.jsx";

const CATEGORIES = ["Park", "Library", "Quiet public space", "Indoor quiet space"];
const LOCATIONS = [
  { label: "Melbourne CBD", latitude: -37.8136, longitude: 144.9631 },
  { label: "Carlton", latitude: -37.8001, longitude: 144.9671 },
  { label: "Docklands", latitude: -37.8183, longitude: 144.9462 },
  { label: "East Melbourne", latitude: -37.8132, longitude: 144.9821 },
  { label: "Southbank", latitude: -37.8233, longitude: 144.9647 },
];

function localDateTimeValue() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 16);
}

function openingLabel(status) {
  return status === "open" ? "Open" : status === "closed" ? "Closed" : "Opening hours unavailable";
}

function selectedDateTimeIso(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

function locationError(error) {
  if (!error) return "Location could not be obtained. Choose a Melbourne location manually.";
  if (error.code === error.PERMISSION_DENIED) return "Location permission was denied. Choose a Melbourne location manually.";
  if (error.code === error.POSITION_UNAVAILABLE) return "Your position is unavailable. Choose a Melbourne location manually.";
  if (error.code === error.TIMEOUT) return "Location lookup timed out. Choose a Melbourne location manually.";
  return "Location could not be obtained. Choose a Melbourne location manually.";
}

export default function RefugesPage() {
  const [location, setLocation] = useState(null);
  const [locationNotice, setLocationNotice] = useState("");
  const [permissionRequested, setPermissionRequested] = useState(false);
  const [manualQuery, setManualQuery] = useState("Melbourne CBD");
  const [radius, setRadius] = useState(1000);
  const [selectedDateTime, setSelectedDateTime] = useState(localDateTimeValue);
  const [enabledCategories, setEnabledCategories] = useState(new Set(CATEGORIES));
  const [refugeQuery, setRefugeQuery] = useState("");
  const [openOnly, setOpenOnly] = useState(false);
  const [refuges, setRefuges] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [emptyMessage, setEmptyMessage] = useState("");
  const [directionsMessage, setDirectionsMessage] = useState("");

  const requestBrowserLocation = useCallback(() => {
    if (permissionRequested) return;
    setPermissionRequested(true);
    if (!globalThis.navigator.geolocation) {
      setLocationNotice("Geolocation is not supported by this browser. Choose a Melbourne location manually.");
      return;
    }
    globalThis.navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          label: "Current location",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
        setLocationNotice("Current location found. Nearby refuge candidates are being updated.");
      },
      (geolocationError) => setLocationNotice(locationError(geolocationError)),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 120_000 },
    );
  }, [permissionRequested]);

  useEffect(() => {
    let cancelled = false;
    if (!globalThis.navigator.permissions?.query) return undefined;
    globalThis.navigator.permissions.query({ name: "geolocation" }).then((result) => {
      if (!cancelled && result.state === "granted") requestBrowserLocation();
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [requestBrowserLocation]);

  useEffect(() => {
    const selectedIso = selectedDateTimeIso(selectedDateTime);
    if (!location || !selectedIso) return undefined;
    const controller = new globalThis.AbortController();
    setLoading(true);
    setError("");
    searchRefuges({
      latitude: location.latitude,
      longitude: location.longitude,
      radius_m: radius,
      selected_datetime: selectedIso,
      limit: 100,
    }, { signal: controller.signal }).then((response) => {
      const next = response.results || [];
      setRefuges(next);
      setEmptyMessage(response.message || "");
      setSelectedId((current) => next.some((item) => item.refuge_id === current) ? current : next[0]?.refuge_id || null);
      setDetails(null);
    }).catch((requestError) => {
      if (requestError.name !== "AbortError") {
        setRefuges([]);
        setError(requestError.message || "Refuge data is temporarily unavailable.");
      }
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [location, radius, selectedDateTime]);

  const visibleRefuges = useMemo(
    () => refuges.filter((item) => enabledCategories.has(item.category)
      && item.name.toLowerCase().includes(refugeQuery.trim().toLowerCase())
      && (!openOnly || item.opening_status === "open")),
    [enabledCategories, openOnly, refugeQuery, refuges],
  );
  const selected = details || visibleRefuges.find((item) => item.refuge_id === selectedId) || null;
  const mapPoints = useMemo(() => visibleRefuges.map((item) => ({
    id: item.refuge_id,
    name: item.name,
    latitude: item.latitude,
    longitude: item.longitude,
    status: item.category,
  })), [visibleRefuges]);

  useEffect(() => {
    if (selectedId && !visibleRefuges.some((item) => item.refuge_id === selectedId)) {
      setSelectedId(visibleRefuges[0]?.refuge_id || null);
      setDetails(null);
    }
  }, [selectedId, visibleRefuges]);

  function chooseManualLocation(event) {
    event.preventDefault();
    const match = LOCATIONS.find((item) => item.label.toLowerCase() === manualQuery.trim().toLowerCase())
      || LOCATIONS.find((item) => item.label.toLowerCase().includes(manualQuery.trim().toLowerCase()));
    if (!match) {
      setLocationNotice("That address is outside the controlled Melbourne location list. Choose one of the suggested suburbs or select a point on the map.");
      return;
    }
    setLocation(match);
    setLocationNotice(`${match.label} selected manually.`);
  }

  function toggleCategory(category) {
    setEnabledCategories((current) => {
      const next = new Set(current);
      if (next.has(category)) next.delete(category); else next.add(category);
      return next;
    });
  }

  async function viewDetails(refuge) {
    setSelectedId(refuge.refuge_id);
    setDirectionsMessage("");
    if (!location) return;
    try {
      setDetails(await getRefugeDetails(refuge.refuge_id, {
        latitude: location.latitude,
        longitude: location.longitude,
        selected_datetime: selectedDateTimeIso(selectedDateTime),
      }));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function requestDirections(refuge) {
    if (!location) return;
    setSelectedId(refuge.refuge_id);
    setDirectionsMessage("Finding walking directions…");
    try {
      const response = await planRoute({
        origin_latitude: location.latitude,
        origin_longitude: location.longitude,
        destination_latitude: refuge.latitude,
        destination_longitude: refuge.longitude,
        travel_mode: "walking",
        preferred_crowd_threshold: 3,
      });
      const route = response.routes?.find((item) => item.is_recommended) || response.routes?.[0];
      setDirectionsMessage(route
        ? `Walking directions found: approximately ${route.estimated_travel_minutes} minutes. Routing conditions may change.`
        : "The route provider returned no walking directions.");
    } catch (requestError) {
      setDirectionsMessage(`${requestError.message} Refuge details remain available.`);
    }
  }

  const chooseMapLocation = useCallback((nextLocation) => {
    setLocation(nextLocation);
    setLocationNotice("Map location selected manually.");
  }, []);

  return (
    <div className="iteration-page page-stack refuge-app">
        <header className="page-heading"><p className="section-kicker">Nearby spaces</p><h1>Find Refuges</h1><p>Find a potential quiet place nearby. Conditions can change.</p></header>

        <section className="control-panel glass-panel" aria-labelledby="location-heading">
          <div><h2 id="location-heading">Choose where to search</h2><p>Location is used only to order nearby candidates by distance.</p></div>
          <button type="button" onClick={requestBrowserLocation} disabled={permissionRequested}>Use my current location</button>
          <form className="manual-location-form" onSubmit={chooseManualLocation}>
            <label htmlFor="manual-location">Search suburb or landmark</label>
            <input id="manual-location" list="melbourne-locations" value={manualQuery} onChange={(event) => setManualQuery(event.target.value)} />
            <datalist id="melbourne-locations">{LOCATIONS.map((item) => <option key={item.label} value={item.label} />)}</datalist>
            <button type="submit">Use selected location</button>
          </form>
          <p className="location-status" role="status" aria-live="polite">
            {location ? `Search centre: ${location.label}.` : "No location selected yet."} {locationNotice}
          </p>
        </section>

        <section className="control-panel glass-panel" aria-labelledby="refuge-filters-heading">
          <div className="results-heading"><div><h2 id="refuge-filters-heading">Filters</h2><p>Choose what is useful now.</p></div></div>
          <div className="filter-grid">
            <label>Search
              <input type="search" value={refugeQuery} onChange={(event) => setRefugeQuery(event.target.value)} placeholder="Search refuge name" />
            </label>
            <label>Search radius
              <select aria-label="Search radius" value={radius} onChange={(event) => setRadius(Number(event.target.value))}>
                <option value="500">500 metres</option><option value="1000">1 kilometre</option><option value="2000">2 kilometres</option><option value="5000">5 kilometres</option>
              </select>
            </label>
            <label>Selected date and time
              <input aria-label="Selected date and time" type="datetime-local" value={selectedDateTime} onChange={(event) => setSelectedDateTime(event.target.value)} required />
            </label>
          </div>
          <label className="checkbox-control open-now-filter"><input type="checkbox" checked={openOnly} onChange={(event) => setOpenOnly(event.target.checked)} /> Open now</label>
          <fieldset className="category-filters"><legend>Categories</legend>{CATEGORIES.map((category) => (
            <label key={category}><input type="checkbox" checked={enabledCategories.has(category)} onChange={() => toggleCategory(category)} /> {category}</label>
          ))}</fieldset>
        </section>

        <div className="iteration-grid">
          <section className="refuge-results glass-panel" aria-labelledby="refuge-results-heading">
            <div className="results-heading"><div><p className="section-kicker">Nearest first</p><h2 id="refuge-results-heading">Refuge candidates</h2></div><span>{visibleRefuges.length} shown</span></div>
            <div aria-live="polite">{loading ? <p>Searching nearby refuge candidates…</p> : null}{error ? <p className="error-state" role="alert">{error}</p> : null}</div>
            {!loading && !error && visibleRefuges.length === 0 ? <div className="empty-state"><h3>No nearby refuge locations were found</h3><p>{emptyMessage || "Change the search, select more categories, or increase the distance."}</p></div> : null}
            <div className="refuge-list">{visibleRefuges.map((item) => (
              <article key={item.refuge_id} className={`refuge-card ${item.refuge_id === selectedId ? "refuge-card--selected" : ""}`}>
                <div className="card-title-row"><div><span className="status-badge">{item.category}</span><h3>{item.name}</h3></div><span>{item.distance_m} m</span></div>
                <p>{item.estimated_travel_minutes} min walk (approx.) · <strong>{openingLabel(item.opening_status)}</strong></p>
                <p>{item.sensory_suitability_description}</p>
                <div className="card-actions">
                  <button type="button" onClick={() => viewDetails(item)}>View details</button>
                  <button type="button" onClick={() => requestDirections(item)}>Directions</button>
                </div>
              </article>
            ))}</div>
          </section>
          <PointMapPanel
            title="Nearby refuge candidates"
            points={mapPoints}
            selectedId={selectedId}
            onSelect={(id) => { setSelectedId(id); setDetails(null); }}
            onChooseLocation={chooseMapLocation}
            label="Sensory refuge candidate map"
            legend="Green Park · Blue Library · Purple Quiet public space · Teal Indoor quiet space. Selected markers have a dark outline."
          />
        </div>

        {selected ? <section className="detail-panel glass-panel" aria-labelledby="refuge-detail-heading">
          <p className="section-kicker">Selected refuge</p><h2 id="refuge-detail-heading">{selected.name}</h2>
          <dl><div><dt>Type</dt><dd>{selected.category}</dd></div><div><dt>Address</dt><dd>{selected.address || "Address unavailable"}</dd></div><div><dt>Distance</dt><dd>{selected.distance_m} m</dd></div><div><dt>Estimated travel</dt><dd>{selected.estimated_travel_minutes} min walk (approx.)</dd></div><div><dt>Hours at selected time</dt><dd>{openingLabel(selected.opening_status)}</dd></div><div><dt>Source</dt><dd>{selected.data_source}</dd></div></dl>
          <p>{selected.limitation_message}</p>{selected.accessibility_notes ? <p><strong>Accessibility:</strong> {selected.accessibility_notes}</p> : null}
          {directionsMessage ? <p role="status" aria-live="polite">{directionsMessage}</p> : null}
        </section> : null}
    </div>
  );
}
