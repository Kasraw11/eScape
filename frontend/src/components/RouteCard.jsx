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


function freshnessLabel(value) {
  const normalized = String(
    value || ""
  ).toLowerCase();

  if (normalized === "fresh") {
    return "Fresh";
  }

  if (normalized === "stale") {
    return "Stale";
  }

  if (normalized === "historical") {
    return "Historical";
  }

  return "Unavailable";
}


function confidenceLabel(
  coverage,
  freshness
) {
  const normalizedFreshness =
    String(
      freshness || ""
    ).toLowerCase();

  if (
    coverage >= 90 &&
    normalizedFreshness === "fresh"
  ) {
    return "High";
  }

  if (
    coverage >= 50 &&
    (
      normalizedFreshness === "fresh" ||
      normalizedFreshness === "stale"
    )
  ) {
    return "Moderate";
  }

  return "Low";
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
      ? 5
      : 0;

  return (
    <div className="sensory-row">
      <strong>
        {label}:
      </strong>{" "}

      <span>
        {normalized}
      </span>

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

  const lowSegments = (
    route.route_segments || []
  ).filter(
    (segment) =>
      String(
        segment.congestion_level || ""
      ).toLowerCase() === "low"
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

  const highSegments = (
    route.route_segments || []
  ).filter(
    (segment) =>
      String(
        segment.congestion_level || ""
      ).toLowerCase() === "high"
  ).length;

  const freshness =
    freshnessLabel(
      route.data_freshness
    );

  const confidence =
    confidenceLabel(
      coverage,
      route.data_freshness
    );

  const limitedData =
    route.sensory_score === null ||
    route.sensory_score === undefined ||
    route.pedestrian_data_availability ===
      "unavailable" ||
    route.data_availability_status ===
      "unavailable" ||
    coverage < 50;

  const partialData =
    !limitedData &&
    coverage < 100;

  const lastUpdated =
    updatedLabel(
      route.observed_at ||
        route.updated_at
    );

  const sensoryScore =
    typeof route.sensory_score ===
    "number"
      ? route.sensory_score.toFixed(2)
      : "Unavailable";

  const preferenceAvailable =
    route.sensory_score !== null &&
    route.sensory_score !== undefined;

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
      {/* Recommended route */}
      {route.is_recommended && (
        <div className="route-card__recommended">
          ★ Recommended calmer route
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
        {/* Route heading */}
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

        {/* ------------------------------------------------------ */}
        {/* Actual environmental crowd condition */}
        {/* ------------------------------------------------------ */}

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

          {/* ---------------------------------------------------- */}
          {/* User preference */}
          {/* ---------------------------------------------------- */}

          {preferenceAvailable && (
            <p
              className={
                route.qualifies_preference
                  ? "route-card__preference route-card__preference--meets"
                  : "route-card__preference route-card__preference--exceeds"
              }
            >
              <strong>
                Your preference:
              </strong>{" "}

              {route.qualifies_preference
                ? "✓ Meets your crowd preference"
                : "⚠ Exceeds your crowd preference"}
            </p>
          )}

          {/* ---------------------------------------------------- */}
          {/* Data confidence */}
          {/* ---------------------------------------------------- */}

          <div className="route-card__data-confidence">
            <p>
              <strong>
                Data confidence:
              </strong>{" "}
              {confidence}
            </p>

            <p>
              <strong>
                Data freshness:
              </strong>{" "}
              {freshness}
            </p>

            <p>
              <strong>
                Crowd-data coverage:
              </strong>{" "}
              {coverage}%
            </p>
          </div>
        </div>

        {/* ------------------------------------------------------ */}
        {/* Data warnings */}
        {/* ------------------------------------------------------ */}

        {limitedData && (
          <p className="route-card__warning">
            ⚠ Sensory data is too limited
            for a reliable recommendation.
          </p>
        )}

        {partialData && (
          <p className="route-card__warning">
            ⚠ Partial sensory data ·{" "}
            {coverage}% crowd-data coverage
          </p>
        )}

        {route.warning_message && (
          <p className="route-card__warning">
            {route.warning_message}
          </p>
        )}

        <p className="route-card__selection-status">
          {selected
            ? "✓ Selected"
            : "Select route"}
        </p>
      </button>

      {/* -------------------------------------------------------- */}
      {/* Start journey */}
      {/* -------------------------------------------------------- */}

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

      {/* -------------------------------------------------------- */}
      {/* Details */}
      {/* -------------------------------------------------------- */}

      <details className="route-card__details">
        <summary>
          View details →
        </summary>

        <div className="route-card__details-content">
          <p>
            <strong>
              Mode:
            </strong>{" "}

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

          <hr />

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

          <hr />

          <p>
            <strong>
              Data freshness:
            </strong>{" "}
            {freshness}
          </p>

          <p>
            <strong>
              Data coverage:
            </strong>{" "}
            {coverage}%
          </p>

          <p>
            <strong>
              Data confidence:
            </strong>{" "}
            {confidence}
          </p>

          {lastUpdated && (
            <p>
              {lastUpdated}
            </p>
          )}

          {route.recommendation_explanation && (
            <>
              <hr />

              <p className="route-card__explanation">
                <strong>
                  Why this route?
                </strong>{" "}
                {
                  route.recommendation_explanation
                }
              </p>
            </>
          )}
        </div>
      </details>
    </article>
  );
}