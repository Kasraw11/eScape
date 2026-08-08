import RouteCard from "./RouteCard.jsx";

export default function RouteList({
  routes,
  selectedRouteIdentifier,
  onSelectRoute,
  onStartJourney,
}) {
  // Do not render anything if there are no routes.
  if (!routes?.length) {
    return null;
  }

  // For the MVP, show at most 3 route options.
  const primaryRoutes = routes.slice(0, 3);

  return (
    <section className="route-list">
      <div className="route-list__header">
        <h2>Route options</h2>

        <p>
          {primaryRoutes.length} option
          {primaryRoutes.length === 1 ? "" : "s"}
        </p>
      </div>

      <div className="route-list__items">
        {primaryRoutes.map((route, index) => (
          <RouteCard
            key={`${route.route_identifier}-${index}`}
            route={route}
            index={index}
            selected={
              route.route_identifier ===
              selectedRouteIdentifier
            }
            onSelectRoute={onSelectRoute}
            onStartJourney={onStartJourney}
          />
        ))}
      </div>
    </section>
  );
}