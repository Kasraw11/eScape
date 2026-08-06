import RouteCard from "./RouteCard.jsx";

export default function RouteList({ routes, selectedRouteIdentifier, onSelectRoute }) {
  if (!routes?.length) {
    return (
      <section className="empty-state">
        <h2>No route alternatives yet</h2>
        <p>Choose a Melbourne CBD origin and destination to compare sensory-aware routes.</p>
      </section>
    );
  }

  return (
    <section className="route-list" aria-labelledby="route-results-heading">
      <h2 id="route-results-heading">Route alternatives</h2>
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
