import SensoryIndicator from "./SensoryIndicator.jsx";


function totalDistance(route) {
  const metres = (
    route.route_segments || []
  ).reduce(
    (sum, segment) =>
      sum + (segment.distance_m || 0),
    0
  );

  if (!metres) {
    return "Unavailable";
  }

  return metres >= 1000
    ? `${(metres / 1000).toFixed(1)} km`
    : `${Math.round(metres)} m`;
}


function displayName(identifier, index) {
  if (!identifier) {
    return `Route ${index + 1}`;
  }

  return identifier
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(
      /\b\w/g,
      (letter) => letter.toUpperCase()
    );
}


function levelLabel(value) {
  const normalized = String(
    value || ""
  ).toLowerCase();

  if (normalized === "low") {
    return "Low";
  }

  if (
    normalized === "moderate" ||
    normalized === "medium"
  ) {
    return "Moderate";
  }

  if (normalized === "high") {
    return "High";
  }

  return "Unavailable";
}


function updatedLabel(value) {
  if (!value) {
    return null;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return `Last updated ${date.toLocaleTimeString(
    [],
    {
      hour: "2-digit",
      minute: "2-digit",
    }
  )}`;
}


function SensoryRow({
  label,
  value,
}) {
  const normalized =
    levelLabel(value);

  const strength =
    normalized === "Low"
      ? 2
      : normalized === "Moderate"
        ? 3
        : normalized === "High"
          ? 4
          : 0;

  return (
    <div className="route-card__sensory-row">
      <strong>{label}:</strong>

      <span>{normalized}</span>

      {strength > 0 && (
        <span
          className={
            `sensory-dots sensory-dots--` +
            normalized.toLowerCase()
          }
          aria-hidden="true"
        >
          {[1, 2, 3, 4, 5].map(
            (dot) => (
              <i
                key={dot}
                className={
                  dot <= strength
                    ? "sensory-dot--active"
                    : ""
                }
              />
            )
          )}
        </span>
      )}
    </div>
  );
}


export default function RouteCard({
  route,
  index,
  selected,
  onSelectRoute,
  onStartJourney,
}) {
  const identifier =
    route.route_identifier ||
    `Alternative ${index + 1}`;

  const coverage = Math.round(
    (route.sensor_coverage_ratio || 0) *
      100
  );

  const highSegments = (
    route.route_segments || []
  ).filter(
    (segment) =>
      String(
        segment.congestion_level || ""
      ).toLowerCase() === "high"
  ).length;

  const moderateSegments = (
    route.route_segments || []
  ).filter((segment) => {
    const level = String(
      segment.congestion_level || ""
    ).toLowerCase();

    return (
      level === "moderate" ||
      level === "medium"
    );
  }).length;

  const lowSegments = (
    route.route_segments || []
  ).filter(
    (segment) =>
      String(
        segment.congestion_level || ""
      ).toLowerCase() === "low"
  ).length;

  const limitedData =
    route.pedestrian_data_availability ===
      "unavailable" ||
    route.data_availability_status ===
      "unavailable" ||
    coverage < 100;

  const lastUpdated =
    updatedLabel(
      route.updated_at ||
      route.observed_at
    );

  const sensoryLevel =
    levelLabel(
      route.sensory_indicator
    );

  const sensoryScore =
    typeof route.sensory_score === "number"
      ? route.sensory_score.toFixed(2)
      : "Unavailable";


  return (
    <article
      className={[
        "route-card",
        route.is_recommended
          ? "route-card--recommended"
          : "",
        selected
          ? "route-card--selected"
          : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >

      {route.is_recommended && (
        <div className="route-card__recommended">
          ★ Recommended
        </div>
      )}


      <button
        className="route-card__select-surface"
        type="button"
        aria-pressed={selected}
        aria-label={
          `Select route ${index + 1}, ` +
          identifier
        }
        onClick={() =>
          onSelectRoute?.(
            route.route_identifier
          )
        }
      >

        <div className="route-card__header">
          <h3>
            {displayName(
              identifier,
              index
            )}
          </h3>

          <div className="route-card__summary">
            <span>
              ◷{" "}
              {
                route.estimated_travel_minutes
              }{" "}
              min
            </span>

            <span>•</span>

            <span>
              ↗ {totalDistance(route)}
            </span>
          </div>
        </div>


        {/* Main sensory information */}
        <div className="route-card__sensory-summary">

          <SensoryRow
            label="Crowd level"
            value={
              route.sensory_indicator
            }
          />

          <p>
            <strong>
              Sensory score:
            </strong>{" "}
            {sensoryScore}
          </p>

          <p>
            <strong>
              Crowd-data coverage:
            </strong>{" "}
            {coverage}%
          </p>

        </div>


        {limitedData && (
          <p className="route-card__warning">
            Limited sensory data
            {coverage > 0
              ? ` · ${coverage}% crowd-data coverage`
              : ""}
          </p>
        )}


        <p className="route-card__selection-status">
          {selected
            ? "✓ Selected"
            : "Select route"}
        </p>

      </button>


      {selected && onStartJourney && (
        <button
          className="route-card__start"
          type="button"
          onClick={() =>
            onStartJourney(
              route.route_identifier
            )
          }
        >
          Start journey →
        </button>
      )}


      <details className="route-card__details">
        <summary>
          View details →
        </summary>

        <div className="route-card__details-content">

          <p>
            <strong>Mode:</strong>{" "}
            {route.travel_mode ===
            "transit"
              ? "Public transport"
              : "Walking"}
          </p>


          <p>
            <strong>
              Matched sensors:
            </strong>{" "}
            {route.matched_sensor_count ||
              0}
          </p>


          <p>
            <strong>
              Low-crowd sections:
            </strong>{" "}
            {lowSegments}
          </p>


          <p>
            <strong>
              Moderate-crowd sections:
            </strong>{" "}
            {moderateSegments}
          </p>


          <p>
            <strong>
              High-crowd sections:
            </strong>{" "}
            {highSegments}
          </p>


          <p>
            <strong>
              Data freshness:
            </strong>{" "}
            {route.data_freshness ||
              "Unavailable"}
          </p>


          {lastUpdated && (
            <p>{lastUpdated}</p>
          )}


          {route.recommendation_explanation && (
            <p className="route-card__explanation">
              {
                route.recommendation_explanation
              }
            </p>
          )}

        </div>
      </details>

    </article>
  );
}