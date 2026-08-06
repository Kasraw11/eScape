export default function DataAvailabilityNotice({ routes = [] }) {
  if (!routes.length) return null;

  const limitedRoutes = routes.filter((route) => route.pedestrian_data_availability !== "available");
  const warnings = limitedRoutes.filter((route) => route.warning_message);
  const hasLimitedData = limitedRoutes.length > 0;

  return (
    <section className={`data-notice ${hasLimitedData ? "data-notice--warning" : ""}`} aria-labelledby="data-notice-title">
      <span className="data-notice__icon" aria-hidden="true">{hasLimitedData ? "i" : "✓"}</span>
      <div>
        <h2 id="data-notice-title">Pedestrian-data coverage</h2>
        <p>
          {hasLimitedData
            ? `${limitedRoutes.length} of ${routes.length} route${routes.length === 1 ? "" : "s"} ${limitedRoutes.length === 1 ? "has" : "have"} partial or unavailable pedestrian data. Sensory comparisons may be less certain.`
            : "Pedestrian-density information is available across all returned routes."}
        </p>
        {warnings.length ? (
          <ul>
            {warnings.map((route, index) => (
              <li key={`${route.route_identifier}-${index}`}><strong>{route.route_identifier}:</strong> {route.warning_message}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}
