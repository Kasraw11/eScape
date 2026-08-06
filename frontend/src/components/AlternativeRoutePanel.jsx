export default function AlternativeRoutePanel({ alternatives = [], noAlternativeMessage, onKeepCurrent, onSelectAlternative, panelRef }) {
  if (!alternatives.length && !noAlternativeMessage) return null;

  return (
    <section className="alternative-panel glass-panel" aria-labelledby="alternative-title" ref={panelRef} tabIndex={-1}>
      <div>
        <p className="section-kicker">Your choice stays active</p>
        <h2 id="alternative-title">Lower-congestion alternatives</h2>
        {alternatives.length ? (
          <p>Review an alternative below. eScape will never switch your selected route without confirmation.</p>
        ) : (
          <p>{noAlternativeMessage}</p>
        )}
      </div>

      {alternatives.map((alternative) => (
        <article className="alternative-card" key={alternative.route_id || alternative.route_identifier}>
          <div>
            <strong>{alternative.route_identifier}</strong>
            <span>{alternative.estimated_travel_minutes} min / {alternative.sensory_indicator}</span>
            <p>{alternative.recommendation_explanation}</p>
          </div>
          <button type="button" className="primary-button primary-button--compact" onClick={() => onSelectAlternative(alternative)}>
            Select alternative route
          </button>
        </article>
      ))}

      <button type="button" className="secondary-button" onClick={onKeepCurrent}>Keep current route</button>
    </section>
  );
}
