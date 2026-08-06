"use client";

import { useState } from "react";

import { planRoute } from "../services/api.js";
import GoogleMapPreview from "./GoogleMapPreview.jsx";
import JourneyForm from "./JourneyForm.jsx";
import LoadingState from "./LoadingState.jsx";
import RouteList from "./RouteList.jsx";

export default function RoutePlannerPage() {
  const [routes, setRoutes] = useState([]);
  const [recommendedRouteIdentifier, setRecommendedRouteIdentifier] = useState(null);
  const [selectedRouteIdentifier, setSelectedRouteIdentifier] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(payload) {
    setLoading(true);
    setError("");
    try {
      const response = await planRoute(payload);
      const nextRoutes = response.routes || [];
      const recommended = response.recommended_route_identifier || null;
      setRoutes(nextRoutes);
      setRecommendedRouteIdentifier(recommended);
      setSelectedRouteIdentifier(recommended || nextRoutes[0]?.route_identifier || null);
    } catch (requestError) {
      setRoutes([]);
      setRecommendedRouteIdentifier(null);
      setSelectedRouteIdentifier(null);
      setError(requestError.message || "Unable to generate routes right now.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="planner-page">
      <section className="planner-hero">
        <div>
          <p className="app-kicker">eScape</p>
          <h1>Sensory-Aware Urban Navigation</h1>
          <p>
            Compare Melbourne CBD route alternatives using travel time, pedestrian data availability, and sensory indicators.
          </p>
        </div>
      </section>

      <section className="planner-layout">
        <div className="planner-panel">
          <h2>Plan a journey</h2>
          <JourneyForm onSubmit={handleSubmit} loading={loading} />
          <GoogleMapPreview
            routes={routes}
            selectedRouteIdentifier={selectedRouteIdentifier}
            onSelectRoute={setSelectedRouteIdentifier}
          />
        </div>

        <div className="results-panel" aria-live="polite">
          {error ? <div className="error-state" role="alert">{error}</div> : null}
          {loading ? <LoadingState /> : null}
          {recommendedRouteIdentifier ? (
            <p className="recommendation-summary">Recommended route: <strong>{recommendedRouteIdentifier}</strong></p>
          ) : null}
          {!loading && routes.length && !recommendedRouteIdentifier ? (
            <p className="recommendation-summary">
              Sensory-aware recommendation cannot be confirmed because all available routes lack sufficient pedestrian data.
            </p>
          ) : null}
          {!loading ? (
            <RouteList
              routes={routes}
              selectedRouteIdentifier={selectedRouteIdentifier}
              onSelectRoute={setSelectedRouteIdentifier}
            />
          ) : null}
        </div>
      </section>
    </main>
  );
}
