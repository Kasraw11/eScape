"use client";

import AccessibleDialog from "./AccessibleDialog.jsx";
import SensoryIndicator from "./SensoryIndicator.jsx";

function routeState(route) {
  return route?.threshold_exceeded ? "Above preference" : "Within preference";
}

export default function AlternativeRoutePanel({ open, currentRoute, alternatives = [], noAlternativeMessage, onKeepCurrent, onSelectAlternative, returnFocusRef }) {
  const alternative = alternatives[0];
  return (
    <AccessibleDialog open={open} onClose={onKeepCurrent} titleId="alternative-title" className="alternative-panel" returnFocusRef={returnFocusRef}>
      <header className="dialog-heading"><div><p className="section-kicker">Your route stays selected</p><h2 id="alternative-title">Lower-congestion alternatives</h2></div><button type="button" className="dialog-close" onClick={onKeepCurrent} aria-label="Close alternative route">×</button></header>
      {currentRoute ? <section className="alternative-summary"><h3>Current route</h3><p><strong>{currentRoute.estimated_travel_minutes} min</strong> · {routeState(currentRoute)}</p><SensoryIndicator indicator={currentRoute.sensory_indicator} /></section> : null}
      {alternative ? <section className="alternative-summary alternative-summary--recommended"><h3>Recommended alternative</h3><p><strong>{alternative.estimated_travel_minutes} min</strong> · {routeState(alternative)}</p><SensoryIndicator indicator={alternative.sensory_indicator} /><p>{alternative.recommendation_explanation}</p><p>{Math.max(0, alternative.estimated_travel_minutes - (currentRoute?.estimated_travel_minutes || 0))} additional minutes</p><button type="button" className="primary-button" onClick={() => onSelectAlternative(alternative)}>Switch route</button></section> : <p>{noAlternativeMessage}</p>}
      <div className="dialog-actions"><button type="button" className="secondary-button" onClick={onKeepCurrent}>Keep current route</button></div>
    </AccessibleDialog>
  );
}
