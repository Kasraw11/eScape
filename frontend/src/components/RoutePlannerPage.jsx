"use client";

import { useState } from "react";

import { planRoute } from "../services/api.js";

import JourneyForm from "./JourneyForm.jsx";
import LoadingState from "./LoadingState.jsx";
import RouteList from "./RouteList.jsx";
import GoogleMapPreview from "./GoogleMapPreview.jsx";

export default function RoutePlannerPage() {
  // Routes returned by the backend.
  const [routes, setRoutes] = useState([]);

  // Keeps track of the currently selected route.
  const [selectedRouteIdentifier, setSelectedRouteIdentifier] =
    useState(null);

  // True while waiting for the backend response.
  const [loading, setLoading] = useState(false);

  // Stores any route-planning error.
  const [error, setError] = useState("");

  /**
   * Sends the origin and destination coordinates
   * from JourneyForm to the FastAPI backend.
   */
  async function handleSubmit(payload) {
    setLoading(true);
    setError("");

    // Clear the previous route search.
    setRoutes([]);
    setSelectedRouteIdentifier(null);

    try {
      const response = await planRoute(payload);

      const returnedRoutes = response.routes || [];

      // Store the real OSRM routes returned by FastAPI.
      setRoutes(returnedRoutes);

      // Automatically select the route recommended by the backend.
      if (response.recommended_route_identifier) {
        setSelectedRouteIdentifier(
          response.recommended_route_identifier
        );
      } else if (returnedRoutes.length > 0) {
        // Fallback: select the first route.
        setSelectedRouteIdentifier(
          returnedRoutes[0].route_identifier
        );
      }
    } catch (requestError) {
      console.error(
        "Route planning error:",
        requestError
      );

      setError(
        requestError.message ||
          "Unable to generate routes right now."
      );
    } finally {
      setLoading(false);
    }
  }

  /**
   * Changes the currently selected route.
   */
  function selectRoute(identifier) {
    setSelectedRouteIdentifier(identifier);
  }

  return (
    <div className="route-planner-page">
      {/* Status messages */}
      <div className="route-planner-status">
        {error && (
          <div className="error-message" role="alert">
            <strong>We couldn't find routes.</strong>
            <p>{error}</p>
          </div>
        )}

        {loading && <LoadingState />}
      </div>

      <div className="plan-workspace">
        {/* Journey planning form */}
        <section
          className="journey-panel glass-panel"
          aria-labelledby="journey-heading"
        >
          <div className="journey-panel__heading">
            <h1 id="journey-heading">
              Plan your journey
            </h1>

            <p>
              Find a calmer way to reach your destination.
            </p>
          </div>

          <JourneyForm
            onSubmit={handleSubmit}
            loading={loading}
          />
        </section>

        {/* Map and route results */}
        <div className="route-visual-column">
          <GoogleMapPreview
            routes={loading ? [] : routes}
            selectedRouteIdentifier={
              selectedRouteIdentifier
            }
            onSelectRoute={selectRoute}
          />

          <RouteList
            routes={loading ? [] : routes}
            selectedRouteIdentifier={
              selectedRouteIdentifier
            }
            onSelectRoute={selectRoute}
          />
        </div>
      </div>
    </div>
  );
}