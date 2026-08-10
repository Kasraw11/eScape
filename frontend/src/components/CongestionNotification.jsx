function formatUpdateTime(value) {
  if (!value) {
    return "just now";
  }

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "just now"
    : date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
}


function getAlertTitle(notification) {
  const level = (
    notification.congestion_level || ""
  ).toLowerCase();

  if (
    notification.threshold_exceeded &&
    level === "high"
  ) {
    return "High crowd detected ahead";
  }

  if (
    notification.threshold_exceeded &&
    level === "moderate"
  ) {
    return "Crowd level exceeds your preference";
  }

  if (level === "high") {
    return "High crowd detected";
  }

  if (level === "moderate") {
    return "Moderate crowd detected";
  }

  return "Congestion update";
}


export default function CongestionNotification({
  notification,
  onReviewAlternative,
  onDismiss,
}) {
  if (!notification) {
    return null;
  }

  const congestionLevel =
    notification.congestion_level
      ? notification.congestion_level
          .charAt(0)
          .toUpperCase() +
        notification.congestion_level.slice(1)
      : "Unknown";

  return (
    <div className="congestion-notification">

      <div className="congestion-notification__header">
        <strong>
          {getAlertTitle(notification)}
        </strong>

        <span>
          {formatUpdateTime(
            notification.updated_at
          )}
        </span>
      </div>


      <p>
        {notification.segment_sequence
          ? `Route segment ${notification.segment_sequence} changed.`
          : "Conditions on your selected route have changed."}
      </p>


      {notification.message && (
        <p>
          {notification.message}
        </p>
      )}


      <p>
        <strong>Current crowd level:</strong>{" "}
        {congestionLevel}
      </p>


      <p>
        {notification.threshold_exceeded
          ? "This section is above your selected crowd comfort level."
          : "This section is within your selected crowd comfort level."}
      </p>


      <div className="congestion-notification__actions">

        {notification.threshold_exceeded && (
          <button
            type="button"
            onClick={onReviewAlternative}
          >
            Review calmer route
          </button>
        )}


        <button
          type="button"
          onClick={onDismiss}
        >
          Dismiss
        </button>

      </div>

    </div>
  );
}