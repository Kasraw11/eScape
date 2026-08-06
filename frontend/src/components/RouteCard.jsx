import DataAvailabilityNotice from "./DataAvailabilityNotice.jsx";
import SensoryIndicator from "./SensoryIndicator.jsx";

export default function RouteCard({ route, index, selected, onSelectRoute }) {
  return (
    <article className={`route-card ${route.is_recommended ? "route-card--recommended" : ""}`}>
      <div className="route-card__header">
        <div>
          <p className="route-card__eyebrow">Route {index + 1}</p>
          <h3>{route.route_identifier || `Alternative ${index + 1}`}</h3>
        </div>
        {route.is_recommended ? <span className="recommended-badge">Recommended lowest sensory route</span> : null}
      </div>
      <div className="route-actions">
        <span>{selected ? "Shown on map" : "Available for map preview"}</span>
        <button type="button" onClick={() => onSelectRoute?.(route.route_identifier)}>
          Show route on map
        </button>
      </div>

      <dl className="route-metrics">
        <div>
          <dt>Estimated travel time</dt>
          <dd>{route.estimated_travel_minutes} min</dd>
        </div>
        <div>
          <dt>Travel mode</dt>
          <dd>{route.travel_mode === "transit" ? "Public transport" : "Walking"}</dd>
        </div>
        <div>
          <dt>Sensory score</dt>
          <dd>{route.sensory_score == null ? "Unconfirmed" : route.sensory_score.toFixed(2)}</dd>
        </div>
        <div>
          <dt>Matched sensors</dt>
          <dd>{route.matched_sensor_count}</dd>
        </div>
        <div>
          <dt>Sensor coverage</dt>
          <dd>{Math.round((route.sensor_coverage_ratio || 0) * 100)}%</dd>
        </div>
      </dl>

      <SensoryIndicator indicator={route.sensory_indicator} />
      <DataAvailabilityNotice availability={route.pedestrian_data_availability} warning={route.warning_message} />

      {route.route_segments?.length ? (
        <details className="segment-details">
          <summary>{route.route_segments.length} route segment{route.route_segments.length === 1 ? "" : "s"}</summary>
          <ol>
            {route.route_segments.map((segment) => (
              <li key={segment.segment_sequence}>
                Segment {segment.segment_sequence}: {segment.duration_seconds ? `${Math.round(segment.duration_seconds / 60)} min` : "duration unknown"},{" "}
                {segment.data_availability === "available" ? "sensor data available" : "sensor data unavailable"}
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </article>
  );
}
