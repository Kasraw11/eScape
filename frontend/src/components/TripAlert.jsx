import AppIcon from "./app/AppIcon.jsx";

function formattedTime(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function TripAlert({ alert, selected, alternativeAvailable = alert.alternativeAvailable, onViewAlternative, onViewMap, onDismiss }) {
  const severity = alert.severity || "Unavailable";
  return (
    <article role="alert" className={`trip-alert trip-alert--${String(severity).toLowerCase()} ${selected ? "trip-alert--selected" : ""}`} data-alert-id={alert.id} tabIndex={selected ? -1 : undefined}>
      <header className="trip-alert__heading">
        <span className="trip-alert__icon"><AppIcon name="bell" size={19} /></span>
        <div><p className="section-kicker">{alert.type === "predictive" ? "Prediction" : "Live route update"}</p><h2>{alert.title}</h2></div>
        <span className={`severity-badge severity-badge--${String(severity).toLowerCase()}`}>{severity}</span>
      </header>
      <p className="trip-alert__area">{alert.area}</p>
      {alert.message ? <p className="trip-alert__message">{alert.message}</p> : null}
      <dl className="trip-alert__facts">
        {alert.predictedTime ? <div><dt>Time</dt><dd>{formattedTime(alert.predictedTime) || "Unavailable"}</dd></div> : null}
        {alert.stressor ? <div><dt>Stressor</dt><dd>{alert.stressor}</dd></div> : null}
        {alert.confidence ? <div><dt>Confidence</dt><dd>{alert.confidence}</dd></div> : null}
        {alert.routeImpact ? <div><dt>Route effect</dt><dd>{alert.routeImpact}</dd></div> : null}
        <div><dt>Last updated</dt><dd>{formattedTime(alert.timestamp) || "Unavailable"}</dd></div>
      </dl>
      {alternativeAvailable ? <p className="trip-alert__availability">Lower-sensory route available.</p> : <p className="trip-alert__availability">No lower-sensory route is currently available.</p>}
      <div className="trip-alert__actions">
        {alternativeAvailable ? <button type="button" className="secondary-button" onClick={() => onViewAlternative(alert)}>View alternative</button> : null}
        {onViewMap ? <button type="button" className="secondary-button" onClick={() => onViewMap(alert)}>View on map</button> : null}
        <button type="button" className="text-button" onClick={() => onDismiss(alert.id)}>Dismiss</button>
      </div>
    </article>
  );
}
