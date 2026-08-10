export default function RouteLegend() {
  return (
    <div className="route-legend" aria-label="Route sensory legend">
      <span><i className="route-legend__line route-legend__line--low" aria-hidden="true" />Low: 0-20/min</span>
      <span><i className="route-legend__line route-legend__line--moderate" aria-hidden="true" />Medium: 21-40/min</span>
      <span><i className="route-legend__line route-legend__line--high" aria-hidden="true" />High: 41+/min</span>
      <span><i className="route-legend__line route-legend__line--unavailable" aria-hidden="true" />Unavailable</span>
    </div>
  );
}
