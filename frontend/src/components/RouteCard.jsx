import SensoryIndicator from "./SensoryIndicator.jsx";

function totalDistance(route) {
  const distance = (route.route_segments || []).reduce((sum, segment) => sum + (segment.distance_m || 0), 0);
  if (!distance) return null;
  return distance >= 1000 ? `${(distance / 1000).toFixed(distance >= 10000 ? 0 : 1)} km` : `${Math.round(distance)} m`;
}

function dataQuality(availability) {
  if (availability === "available") return "Good";
  if (availability === "partial") return "Partial";
  return "Unavailable";
}

function formatUpdatedAt(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not available" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function RouteCard({ route, index, selected, onSelectRoute }) {
  const identifier = route.route_identifier || `Alternative ${index + 1}`;
  const distance = totalDistance(route);
  const highSegments = (route.route_segments || []).filter((segment) => segment.congestion_level === "high").length;

  function selectRoute() {
    onSelectRoute?.(route.route_identifier);
  }

  return (
    <article
      className={`route-card ${route.is_recommended ? "route-card--recommended" : ""} ${selected ? "route-card--selected" : ""}`}
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      aria-label={`Select route ${index + 1}, ${identifier}`}
      onClick={selectRoute}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectRoute();
        }
      }}
    >
      <div className="route-card__header">
        <div className="route-card__identity">
          <span className="route-card__number" aria-hidden="true">{index + 1}</span>
          <div>
            <p className="route-card__eyebrow">Route {index + 1}</p>
            <h3>{identifier}</h3>
          </div>
        </div>
        {route.is_recommended ? <span className="recommended-badge"><span aria-hidden="true">★</span> Recommended</span> : null}
      </div>

      <div className="route-card__primary">
        <div className="travel-time">
          <strong>{route.estimated_travel_minutes}</strong>
          <span>min</span>
        </div>
        <SensoryIndicator indicator={route.sensory_indicator} />
      </div>

      <dl className="route-metrics">
        {distance ? <div><dt>Distance</dt><dd>{distance}</dd></div> : null}
        <div><dt>Mode</dt><dd>{route.travel_mode === "transit" ? "Public transport" : "Walking"}</dd></div>
        <div><dt>Data quality</dt><dd>{dataQuality(route.pedestrian_data_availability)}</dd></div>
        <div><dt>Sensor coverage</dt><dd>{Math.round((route.sensor_coverage_ratio || 0) * 100)}% · {route.matched_sensor_count || 0} sensor{route.matched_sensor_count === 1 ? "" : "s"}</dd></div>
        <div><dt>High-congestion segments</dt><dd>{highSegments}</dd></div>
        <div><dt>Data freshness</dt><dd>{route.data_freshness || "unavailable"}</dd></div>
        <div><dt>Last updated</dt><dd>{formatUpdatedAt(route.updated_at || route.observed_at)}</dd></div>
      </dl>

      {route.threshold_exceeded === true ? <p className="threshold-status threshold-status--exceeded">Crowd preference exceeded</p> : null}
      {route.threshold_exceeded === false ? <p className="threshold-status">Within your crowd preference</p> : null}
      {route.recommendation_explanation ? <p className="route-card__explanation">{route.recommendation_explanation}</p> : null}

      <div className="route-card__footer">
        <span className={selected ? "selected-label selected-label--active" : "selected-label"}>
          <span aria-hidden="true">{selected ? "✓" : "○"}</span>{selected ? "Selected on map" : "Available to preview"}
        </span>
        <span className="route-card__select-label">{selected ? "Selected" : "Select route"}</span>
      </div>
    </article>
  );
}
