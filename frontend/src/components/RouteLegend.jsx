export default function RouteLegend() {
  return (
    <div className="route-legend" aria-label="Route congestion legend">
      <span><i className="route-legend__line route-legend__line--low" aria-hidden="true" />Low-congestion segment</span>
      <span><i className="route-legend__line route-legend__line--high" aria-hidden="true" />High-congestion corridor</span>
      <span><i className="route-legend__line route-legend__line--unavailable" aria-hidden="true" />Congestion unavailable</span>
      <span><strong>Thicker line</strong> Selected or recommended route</span>
    </div>
  );
}
