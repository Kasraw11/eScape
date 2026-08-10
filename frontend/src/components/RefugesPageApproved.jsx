"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getRefugeDetails, getRefugeFeedbackSummary, planRoute, searchRefuges } from "../services/api.js";
import AccessibleDialog from "./AccessibleDialog.jsx";
import PointMapPanel from "./PointMapPanel.jsx";
import RefugeFeedbackDialog from "./RefugeFeedbackDialog.jsx";
import RefugeFeedbackSummary from "./RefugeFeedbackSummary.jsx";

const CATEGORIES = ["Park", "Library", "Quiet public space", "Indoor quiet space"];
const CATEGORY_FILTERS = [
  { label: "Parks", accessibleLabel: "Park", categories: ["Park"] },
  { label: "Libraries", accessibleLabel: "Library", categories: ["Library"] },
  { label: "Quiet spaces", accessibleLabel: "Quiet spaces", categories: ["Quiet public space", "Indoor quiet space"] },
];
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

function distanceLabel(distanceM) {
  if (!Number.isFinite(distanceM)) return "Distance unavailable";
  return distanceM < 1000 ? `${distanceM} m` : `${(distanceM / 1000).toFixed(1)} km`;
}

function routeDistanceLabel(route) {
  const metres = (route?.route_segments || []).reduce(
    (total, segment) => total + Number(segment.distance_m || 0),
    0,
  );

  if (!metres) return "Distance unavailable";
  return metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`;
}

function routePedestrianSummary(route) {
  const segments = (route?.route_segments || []).filter(
    (segment) => Number.isFinite(Number(segment.pedestrian_count)),
  );

  if (!segments.length) {
    return { average: null, peak: null, low: 0, medium: 0, high: 0 };
  }

  const counts = segments.map((segment) => Number(segment.pedestrian_count));
  return {
    average: Math.round(counts.reduce((sum, value) => sum + value, 0) / counts.length),
    peak: Math.max(...counts),
    low: counts.filter((value) => value <= 20).length,
    medium: counts.filter((value) => value > 20 && value <= 40).length,
    high: counts.filter((value) => value > 40).length,
  };
}

function routeSensoryLabel(value) {
  if (!value) return "Unavailable";
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function RefugesPage() {
  const [location, setLocation] = useState(null);
  const [locationNotice, setLocationNotice] = useState("");
  const [permissionRequested, setPermissionRequested] = useState(false);
  const [manualQuery, setManualQuery] = useState("Melbourne CBD");
  const [radius, setRadius] = useState(2000);
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
  const [directionRoute, setDirectionRoute] = useState(null);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [feedbackSummary, setFeedbackSummary] = useState(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackError, setFeedbackError] = useState("");
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [feedbackVersion, setFeedbackVersion] = useState(0);
  const [feedbackNotice, setFeedbackNotice] = useState("");
  const leaveFeedbackRef = useRef(null);
  const detailsReturnRef = useRef(null);

  const requestBrowserLocation = useCallback(() => {
    if (permissionRequested) return;
    setPermissionRequested(true);
    if (!globalThis.navigator.geolocation) {
      setLocationNotice("Geolocation is not supported by this browser. Choose a Melbourne location manually.");
      return;
    }
    globalThis.navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({ label: "Current location", latitude: position.coords.latitude, longitude: position.coords.longitude });
        setLocationNotice("Current location found. Nearby refuges are being updated.");
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
    searchRefuges({ latitude: location.latitude, longitude: location.longitude, radius_m: radius, selected_datetime: selectedIso, limit: 100 }, { signal: controller.signal })
      .then((response) => {
        const next = response.results || [];
        setRefuges(next);
        setEmptyMessage(response.message || "");
        setSelectedId((current) => next.some((item) => item.refuge_id === current) ? current : next[0]?.refuge_id || null);
        setDetails(null);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          setRefuges([]);
          setError(requestError.message || "Refuge data is temporarily unavailable.");
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [location, radius, selectedDateTime]);

  const visibleRefuges = useMemo(
    () => refuges.filter((item) => enabledCategories.has(item.category)
      && item.name.toLowerCase().includes(refugeQuery.trim().toLowerCase())
      && (!openOnly || item.opening_status === "open")),
    [enabledCategories, openOnly, refugeQuery, refuges],
  );
  const selected = details || visibleRefuges.find((item) => item.refuge_id === selectedId) || null;
  const mapPoints = useMemo(() => visibleRefuges.map((item) => ({ id: item.refuge_id, name: item.name, latitude: item.latitude, longitude: item.longitude, status: item.category })), [visibleRefuges]);

  useEffect(() => {
    if (selectedId && !visibleRefuges.some((item) => item.refuge_id === selectedId)) {
      setSelectedId(visibleRefuges[0]?.refuge_id || null);
      setDetails(null);
    }
  }, [selectedId, visibleRefuges]);

  useEffect(() => {
    if (!selectedId) {
      setFeedbackSummary(null);
      return undefined;
    }
    const controller = new globalThis.AbortController();
    setFeedbackLoading(true);
    setFeedbackError("");
    getRefugeFeedbackSummary(selectedId, { signal: controller.signal })
      .then(setFeedbackSummary)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          setFeedbackSummary(null);
          setFeedbackError(requestError.message || "Community feedback is temporarily unavailable.");
        }
      })
      .finally(() => { if (!controller.signal.aborted) setFeedbackLoading(false); });
    return () => controller.abort();
  }, [feedbackVersion, selectedId]);

  function chooseManualLocation(event) {
    event.preventDefault();
    const match = LOCATIONS.find((item) => item.label.toLowerCase() === manualQuery.trim().toLowerCase())
      || LOCATIONS.find((item) => item.label.toLowerCase().includes(manualQuery.trim().toLowerCase()));
    if (!match) {
      setLocationNotice("That address is outside the controlled Melbourne location list. Choose a suggested suburb or select a point on the map.");
      return;
    }
    setLocation(match);
    setLocationNotice(`${match.label} selected manually.`);
  }

  function toggleCategoryGroup(categories) {
    setEnabledCategories((current) => {
      const next = new Set(current);
      const allEnabled = categories.every((category) => next.has(category));
      categories.forEach((category) => allEnabled ? next.delete(category) : next.add(category));
      return next;
    });
  }

  const selectRefuge = useCallback(async (refugeOrId) => {
    const refuge = typeof refugeOrId === "object" ? refugeOrId : visibleRefuges.find((item) => String(item.refuge_id) === String(refugeOrId));
    if (!refuge) return;
    setSelectedId(refuge.refuge_id);
    setDetails(null);
    setDirectionsMessage("");
    setDirectionRoute(null);
    setFeedbackNotice("");
    try {
      const parameters = location ? { latitude: location.latitude, longitude: location.longitude, selected_datetime: selectedDateTimeIso(selectedDateTime) } : {};
      setDetails(await getRefugeDetails(refuge.refuge_id, parameters));
    } catch (requestError) {
      setError(requestError.message || "Refuge details are temporarily unavailable.");
    }
  }, [location, selectedDateTime, visibleRefuges]);

  async function openDetails(refuge, trigger) {
    detailsReturnRef.current = trigger;
    setDetailsModalOpen(true);
    await selectRefuge(refuge);
  }

  async function requestDirections(refuge) {
    if (!location) {
      setDirectionsMessage("Choose a location before requesting directions.");
      return;
    }
    setSelectedId(refuge.refuge_id);
    setDetails(null);
    setDirectionsMessage("Finding walking directions…");
    setDirectionRoute(null);
    try {
      const response = await planRoute({ origin_latitude: location.latitude, origin_longitude: location.longitude, destination_latitude: refuge.latitude, destination_longitude: refuge.longitude, travel_mode: "walking", preferred_crowd_threshold: 3 });
      const route = response.routes?.find((item) => item.is_recommended) || response.routes?.[0];
      if (route) {
        setDirectionRoute(route);
        setDirectionsMessage(`Walking to ${refuge.name}: approximately ${route.estimated_travel_minutes} minutes · ${routeDistanceLabel(route)}. Routing conditions may change.`);
        setDetailsModalOpen(false);
      } else {
        setDirectionsMessage("The route provider returned no walking directions.");
      }
    } catch (requestError) {
      setDirectionsMessage(`${requestError.message} Refuge details remain available.`);
    }
  }

  const chooseMapLocation = useCallback((nextLocation) => {
    setLocation(nextLocation);
    setLocationNotice("Map location selected manually.");
  }, []);

  function feedbackSubmitted() {
    setFeedbackModalOpen(false);
    setFeedbackNotice("Feedback submitted");
    setFeedbackVersion((current) => current + 1);
  }

  const allCategoriesEnabled = enabledCategories.size === CATEGORIES.length;

  return (
    <div className="iteration-page page-stack refuge-app">
      <header className="page-heading refuge-page-heading">
        <p className="section-kicker">Nearby spaces</p><h1>Find refuges</h1><p>Discover quiet, welcoming spaces near you to take a break and reset.</p>
      </header>

      <div className="refuge-layout">
        <section className="refuge-controls glass-panel" aria-labelledby="location-heading">
          <div className="refuge-section-heading"><h2 id="location-heading">Location</h2></div>
          <button type="button" className="current-location-button" onClick={requestBrowserLocation} disabled={permissionRequested}><span>{location?.label || "Use my current location"}</span><span aria-hidden="true">◎</span></button>
          <form className="manual-location-form refuge-manual-location" onSubmit={chooseManualLocation}>
            <label htmlFor="manual-location">Search suburb or landmark</label>
            <div><input id="manual-location" list="melbourne-locations" value={manualQuery} onChange={(event) => setManualQuery(event.target.value)} /><button type="submit">Use selected location</button></div>
            <datalist id="melbourne-locations">{LOCATIONS.map((item) => <option key={item.label} value={item.label} />)}</datalist>
          </form>
          <p className="location-status" role="status" aria-live="polite">{location ? `Search centre: ${location.label}.` : "No location selected yet."} {locationNotice}</p>

          <div className="refuge-filter-heading"><h2 id="refuge-filters-heading">Filters</h2><button type="button" onClick={() => { setEnabledCategories(new Set(CATEGORIES)); setRefugeQuery(""); setOpenOnly(false); }}>Reset</button></div>
          <label className="refuge-search">Search refuges<input type="search" value={refugeQuery} onChange={(event) => setRefugeQuery(event.target.value)} placeholder="Search by name" /></label>
          <fieldset className="category-filters refuge-filter-pills" aria-labelledby="refuge-filters-heading">
            <legend className="sr-only">Refuge types</legend>
            <label><input type="checkbox" aria-label="All types" checked={allCategoriesEnabled} onChange={() => setEnabledCategories(allCategoriesEnabled ? new Set() : new Set(CATEGORIES))} /><span>All types</span></label>
            {CATEGORY_FILTERS.map((filter) => {
              const checked = filter.categories.every((category) => enabledCategories.has(category));
              return <label key={filter.label}><input type="checkbox" aria-label={filter.accessibleLabel} checked={checked} onChange={() => toggleCategoryGroup(filter.categories)} /><span>{filter.label}</span></label>;
            })}
          </fieldset>
          <div className="refuge-compact-filters">
            <label>Sort by<select aria-label="Sort by" defaultValue="nearest"><option value="nearest">Nearest</option></select></label>
            <label>Max distance<select aria-label="Search radius" value={radius} onChange={(event) => setRadius(Number(event.target.value))}><option value="500">500 m</option><option value="1000">1 km</option><option value="2000">2 km</option><option value="5000">5 km</option></select></label>
          </div>
          <label className="checkbox-control open-now-filter"><input type="checkbox" checked={openOnly} onChange={(event) => setOpenOnly(event.target.checked)} /> Open now</label>
          <details className="refuge-more-filters"><summary>Date and time</summary><label>Selected date and time<input aria-label="Selected date and time" type="datetime-local" value={selectedDateTime} onChange={(event) => setSelectedDateTime(event.target.value)} required /></label></details>
        </section>

        <div className="refuge-map-area">
          <PointMapPanel title="Nearby refuges" points={mapPoints} selectedId={selectedId} onSelect={selectRefuge} onChooseLocation={chooseMapLocation} routePoints={directionRoute?.points || []} routeSegments={directionRoute?.route_segments || []} routeSummary={directionsMessage} label="Sensory refuge map" legend="Route: green Low (0-20/min) · amber Medium (21-40/min) · red High (41+/min) · grey Unavailable. Small route dots are pedestrian sensors. Refuge markers: green Park · blue Library · purple Quiet space." />
        </div>

        <section className="refuge-results glass-panel" aria-labelledby="refuge-results-heading">
          <div className="results-heading"><div><p className="section-kicker">Nearest first</p><h2 id="refuge-results-heading">Refuge results</h2></div><span>{visibleRefuges.length} shown</span></div>
          <div aria-live="polite">{loading ? <p>Searching nearby refuges…</p> : null}{error ? <p className="error-state" role="alert">{error}</p> : null}</div>
          {!loading && !error && visibleRefuges.length === 0 ? <div className="empty-state"><h3>No nearby refuge locations were found</h3><p>{emptyMessage || "Change the search, select more types, or increase the distance."}</p></div> : null}
          <div className="refuge-list">{visibleRefuges.map((item) => (
            <article key={item.refuge_id} className={`refuge-card ${item.refuge_id === selectedId ? "refuge-card--selected" : ""}`}>
              <button type="button" className="refuge-card__select" onClick={() => selectRefuge(item)} aria-label={`View details for ${item.name}`}>
                <span className="refuge-card__heading"><span><strong>{item.name}</strong><small>{item.category}</small></span><strong>{distanceLabel(item.distance_m)}</strong></span>
                <span className="refuge-card__description">{item.sensory_suitability_description}</span>
                <span className="refuge-card__meta"><span><strong>{openingLabel(item.opening_status)}</strong>{item.opening_status === "open" && item.opening_hours_summary ? <small>{item.opening_hours_summary}</small> : null}</span><span>{item.estimated_travel_minutes} min walk</span></span>
              </button>
              <h3 className="sr-only">{item.name}</h3>
              <div className="card-actions"><button type="button" onClick={(event) => openDetails(item, event.currentTarget)}>View details</button><button type="button" onClick={() => requestDirections(item)}>Directions</button></div>
            </article>
          ))}</div>
        </section>

        {selected && detailsModalOpen ? <AccessibleDialog open={detailsModalOpen} onClose={() => setDetailsModalOpen(false)} titleId="refuge-detail-heading" className="refuge-detail-dialog" returnFocusRef={detailsReturnRef}><section className="detail-panel refuge-detail" aria-labelledby="refuge-detail-heading">
          <div className="refuge-detail__heading"><div><p className="section-kicker">Selected refuge</p><h2 id="refuge-detail-heading">{selected.name}</h2><p>{selected.category} · {distanceLabel(selected.distance_m)}</p></div><div className="refuge-detail__actions"><span className={`opening-badge opening-badge--${selected.opening_status}`}>{openingLabel(selected.opening_status)}</span><button type="button" className="dialog-close" onClick={() => setDetailsModalOpen(false)} aria-label="Close refuge details">×</button></div></div>
          <p className="refuge-detail__description">{selected.sensory_suitability_description || "Description unavailable"}</p>
          <dl className="refuge-detail__facts">
            <div><dt>Opening hours</dt><dd>{selected.opening_hours_summary || selected.operating_hours || openingLabel(selected.opening_status)}</dd></div>
            <div><dt>Walking time</dt><dd>{selected.estimated_travel_minutes} min · {distanceLabel(selected.distance_m)}</dd></div>
            <div><dt>Accessibility</dt><dd>{selected.accessibility_notes || "Accessibility information unavailable"}</dd></div>
            <div><dt>Sensory notes</dt><dd>{selected.sensory_notes || "Detailed sensory information unavailable"}</dd></div>
          </dl>
          <button type="button" className="primary-button refuge-directions-button" onClick={() => requestDirections(selected)}>Get directions <span aria-hidden="true">→</span></button>
          {directionsMessage ? <p role="status" aria-live="polite" className="directions-status">{directionsMessage}</p> : null}
          {directionRoute ? (
            <section className="route-sensory-summary" aria-labelledby="refuge-route-sensory-heading">
              <h3 id="refuge-route-sensory-heading">Route sensory summary</h3>
              <dl>
                <div><dt>Sensory level</dt><dd>{routeSensoryLabel(directionRoute.sensory_indicator)}</dd></div>
                <div><dt>Crowd-data coverage</dt><dd>{Math.round((directionRoute.sensor_coverage_ratio || 0) * 100)}%</dd></div>
                <div><dt>Matched sensors</dt><dd>{directionRoute.matched_sensor_count || 0}</dd></div>
                <div><dt>Average pedestrians/min</dt><dd>{routePedestrianSummary(directionRoute).average ?? "Unavailable"}</dd></div>
                <div><dt>Peak pedestrians/min</dt><dd>{routePedestrianSummary(directionRoute).peak ?? "Unavailable"}</dd></div>
                <div><dt>High-crowd sections</dt><dd>{routePedestrianSummary(directionRoute).high}</dd></div>
              </dl>
              <p>{directionRoute.recommendation_explanation || "This route uses the same crowd scoring logic as the journey planner."}</p>
            </section>
          ) : null}
          <RefugeFeedbackSummary summary={feedbackSummary} loading={feedbackLoading} error={feedbackError} onLeaveFeedback={() => setFeedbackModalOpen(true)} leaveFeedbackRef={leaveFeedbackRef} />
        </section></AccessibleDialog> : null}
      </div>

      <RefugeFeedbackDialog open={feedbackModalOpen} refuge={selected} onClose={() => setFeedbackModalOpen(false)} onSubmitted={feedbackSubmitted} returnFocusRef={leaveFeedbackRef} />
      {feedbackNotice ? <div className="refuge-feedback-toast" role="status" aria-live="polite">{feedbackNotice}</div> : null}
    </div>
  );
}
