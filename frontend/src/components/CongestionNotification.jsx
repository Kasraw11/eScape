function formatUpdateTime(value) {
  if (!value) return "just now";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "just now" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function CongestionNotification({ notification, onReviewAlternative, onDismiss }) {
  if (!notification) return null;

  return (
    <aside className="congestion-alert" role="alert" aria-live="assertive">
      <div>
        <p className="section-kicker">Congestion update / {formatUpdateTime(notification.updated_at)}</p>
        <h2>{notification.segment_sequence ? `Route segment ${notification.segment_sequence} changed` : "Selected route changed"}</h2>
        <p>{notification.message}</p>
        <p><strong>Current state:</strong> {notification.congestion_level} congestion. {notification.threshold_exceeded ? "Your threshold is exceeded." : "Within your selected threshold."}</p>
      </div>
      <div className="congestion-alert__actions">
        {notification.threshold_exceeded ? (
          <button type="button" className="secondary-button" onClick={onReviewAlternative}>Review alternative route</button>
        ) : null}
        <button type="button" className="text-button" onClick={onDismiss}>Dismiss update</button>
      </div>
    </aside>
  );
}
