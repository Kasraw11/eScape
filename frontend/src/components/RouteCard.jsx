import SensoryIndicator from "./SensoryIndicator.jsx";

function totalDistance(route) {
  const metres = (route.route_segments || []).reduce((sum, segment) => sum + (segment.distance_m || 0), 0);
  if (!metres) return "Unavailable";
  return metres >= 1000 ? `${(metres / 1000).toFixed(1)} km` : `${Math.round(metres)} m`;
}

function displayName(identifier, index) {
  if (!identifier) return `Route ${index + 1}`;
  return identifier.replaceAll("_", " ").replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function levelLabel(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "low") return "Low";
  if (normalized === "moderate" || normalized === "medium") return "Moderate";
  if (normalized === "high") return "High";
  return "Unavailable";
}

function updatedLabel(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : `Last updated ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function SensoryRow({ label, value }) {
  const normalized = levelLabel(value);
  const strength = normalized === "Low" ? 2 : normalized === "Moderate" ? 3 : normalized === "High" ? 4 : 0;
  return <div className="route-sensory-row"><span>{label}</span><strong>{normalized}</strong>{strength ? <span className={`sensory-dots sensory-dots--${normalized.toLowerCase()}`} aria-hidden="true">{[1, 2, 3, 4, 5].map((dot) => <i key={dot} className={dot <= strength ? "sensory-dot--active" : ""} />)}</span> : null}</div>;
}

export default function RouteCard({ route, index, selected, onSelectRoute, onStartJourney }) {
  const identifier = route.route_identifier || `Alternative ${index + 1}`;
  const coverage = Math.round((route.sensor_coverage_ratio || 0) * 100);
  const highSegments = (route.route_segments || []).filter((segment) => segment.congestion_level === "high").length;
  const limitedData = route.pedestrian_data_availability === "unavailable" || route.data_availability_status === "unavailable" || coverage < 100;

  return (
    <article className={`route-card ${route.is_recommended ? "route-card--recommended" : ""} ${selected ? "route-card--selected" : ""}`}>
      {route.is_recommended ? <span className="recommended-badge"><span aria-hidden="true">★</span> Recommended</span> : null}
      <button className="route-card__select-surface" type="button" aria-pressed={selected} aria-label={`Select route ${index + 1}, ${identifier}`} onClick={() => onSelectRoute?.(route.route_identifier)}>
        <div className="route-card__header"><h3>{displayName(identifier, index)}</h3><SensoryIndicator indicator={route.sensory_indicator} /></div>
        <div className="route-card__journey-metrics"><span>◷ <strong>{route.estimated_travel_minutes} min</strong></span><span aria-hidden="true">•</span><span>↗ <strong>{totalDistance(route)}</strong></span></div>
        <div className="route-card__sensory-summary"><SensoryRow label="Crowding" value={route.sensory_indicator} /><SensoryRow label="Noise" value={route.noise_level} /><SensoryRow label="Brightness" value={route.brightness_level} /></div>
        {limitedData ? <p className="route-card__data-note">Limited sensory data{coverage ? ` · ${coverage}% crowd-data coverage` : ""}</p> : null}
        {selected ? <p className="route-card__selection-note"><span aria-hidden="true">✓</span> Selected. Selecting a route does not start your trip.</p> : <span className="route-card__select-label">Select route</span>}
      </button>
      {selected && onStartJourney ? <button className="route-card__start" type="button" onClick={() => onStartJourney(route.route_identifier)}>Start journey <span aria-hidden="true">→</span></button> : null}
      <details className="route-card__details"><summary>View details <span aria-hidden="true">→</span></summary><dl><div><dt>Mode</dt><dd>{route.travel_mode === "transit" ? "Public transport" : "Walking"}</dd></div><div><dt>Crowd-data coverage</dt><dd>{coverage}% crowd-data coverage</dd></div><div><dt>Matched sensors</dt><dd>{route.matched_sensor_count || 0}</dd></div><div><dt>High-crowd sections</dt><dd>{highSegments}</dd></div><div><dt>Data freshness</dt><dd>{route.data_freshness || "Unavailable"}</dd></div></dl>{updatedLabel(route.updated_at || route.observed_at) ? <p className="route-card__updated">{updatedLabel(route.updated_at || route.observed_at)}</p> : null}{route.recommendation_explanation ? <p>{route.recommendation_explanation}</p> : null}</details>
    </article>
  );
}
