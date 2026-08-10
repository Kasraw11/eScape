import AppIcon from "./app/AppIcon.jsx";


function formattedTime(value) {
  if (!value) return null;

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? null
    : date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
}


export default function TripAlert({
  alert,
  selected,
  alternativeAvailable = alert.alternativeAvailable,
  onViewAlternative,
  onViewMap,
  onDismiss,
}) {
  const severity =
    alert.severity || "Unavailable";

  const thresholdExceeded =
    alert.threshold_exceeded === true;

  return (
    <article
      role="alert"
      className={
        `trip-alert trip-alert--${String(
          severity
        ).toLowerCase()} ${
          selected
            ? "trip-alert--selected"
            : ""
        }`
      }
      data-alert-id={alert.id}
      tabIndex={
        selected ? -1 : undefined
      }
    >

      <div className="trip-alert__header">
        <span>
          {alert.type === "predictive"
            ? "Prediction"
            : "Live route update"}
        </span>

        <span
          className={
            `severity-badge severity-badge--${String(
              severity
            ).toLowerCase()}`
          }
        >
          {severity}
        </span>
      </div>


      <h3>
        {alert.title}
      </h3>


      {alert.area && (
        <p>
          <strong>Area:</strong>{" "}
          {alert.area}
        </p>
      )}


      {alert.message && (
        <p>
          {alert.message}
        </p>
      )}


      {thresholdExceeded ? (
        <p>
          <strong>
            This crowd level exceeds your
            selected comfort level.
          </strong>
        </p>
      ) : (
        <p>
          This crowd level is within your
          selected comfort level.
        </p>
      )}


      {alert.predictedTime && (
        <p>
          <strong>Time:</strong>{" "}
          {formattedTime(
            alert.predictedTime
          ) || "Unavailable"}
        </p>
      )}


      {alert.stressor && (
        <p>
          <strong>Stressor:</strong>{" "}
          {alert.stressor}
        </p>
      )}


      {alert.confidence && (
        <p>
          <strong>Confidence:</strong>{" "}
          {alert.confidence}
        </p>
      )}


      {alert.routeImpact && (
        <p>
          <strong>Route effect:</strong>{" "}
          {alert.routeImpact}
        </p>
      )}


      <p>
        <strong>Last updated:</strong>{" "}
        {formattedTime(
          alert.timestamp
        ) || "Unavailable"}
      </p>


      <p>
        {alternativeAvailable
          ? "A calmer route is available."
          : "No calmer route is currently available."}
      </p>


      <div className="trip-alert__actions">

        {alternativeAvailable &&
        thresholdExceeded ? (
          <button
            type="button"
            className="secondary-button"
            onClick={() =>
              onViewAlternative(alert)
            }
          >
            View calmer route
          </button>
        ) : null}


        {onViewMap ? (
          <button
            type="button"
            className="secondary-button"
            onClick={() =>
              onViewMap(alert)
            }
          >
            View on map
          </button>
        ) : null}


        <button
          type="button"
          className="text-button"
          onClick={() =>
            onDismiss(alert.id)
          }
        >
          Dismiss
        </button>

      </div>

    </article>
  );
}