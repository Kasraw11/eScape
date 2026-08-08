import RouteCard from "./RouteCard.jsx";

export default function RouteList({ routes, selectedRouteIdentifier, onSelectRoute, onStartJourney }) {
  if (!routes?.length) return null;
  const primaryRoutes = routes.slice(0, 3);

  return (
    <section className="route-list glass-panel" aria-labelledby="route-results-heading">
      <div className="route-list__heading"><h2 id="route-results-heading">Route options</h2><span>{primaryRoutes.length} option{primaryRoutes.length === 1 ? "" : "s"}</span></div>
      <div className="route-list__items">
        {primaryRoutes.map((route, index) => (
          <RouteCard
            key={`${route.route_identifier}-${index}`}
            route={route}
            index={index}
            selected={route.route_identifier === selectedRouteIdentifier}
            onSelectRoute={onSelectRoute}
            onStartJourney={onStartJourney}
          />
        ))}
      </div>
    </section>
  );
}
