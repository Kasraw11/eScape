import RouteCard from "./RouteCard.jsx";

export default function RouteList({ routes, selectedRouteIdentifier, onSelectRoute }) {
  if (!routes?.length) {
    return (
      <section className="empty-state" aria-labelledby="route-results-heading">
        <div className="empty-state__icon" aria-hidden="true">↝</div>
        <h2 id="route-results-heading">Your route options will appear here</h2>
        <p>Choose a Melbourne CBD origin and destination to compare sensory-aware routes.</p>
      </section>
    );
  }

  return (
    <section className="route-list glass-panel" aria-labelledby="route-results-heading">
      <div className="panel-heading route-list__heading">
        <div>
          <p className="section-kicker">Comparison</p>
          <h2 id="route-results-heading">Route options</h2>
        </div>
        <span className="route-count">{routes.length} route{routes.length === 1 ? "" : "s"} found</span>
      </div>
      <div className="route-list__items">
        {routes.map((route, index) => (
          <RouteCard
            key={`${route.route_identifier}-${index}`}
            route={route}
            index={index}
            selected={route.route_identifier === selectedRouteIdentifier}
            onSelectRoute={onSelectRoute}
          />
        ))}
      </div>
    </section>
  );
}
