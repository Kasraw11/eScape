export default function RouteLegend() {
  return (
    <div className="route-legend" aria-label="Route sensory legend">
      <span><i className="route-legend__line route-legend__line--low" aria-hidden="true" />Low</span>
      <span><i className="route-legend__line route-legend__line--moderate" aria-hidden="true" />Moderate</span>
      <span><i className="route-legend__line route-legend__line--high" aria-hidden="true" />High</span>
      <span><i className="route-legend__line route-legend__line--unavailable" aria-hidden="true" />Unavailable</span>
    </div>
  );
}
