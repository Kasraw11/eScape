"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { planRoute } from "../services/api.js";
import useCongestionPolling from "../hooks/useCongestionPolling.js";
import AlternativeRoutePanel from "./AlternativeRoutePanel.jsx";
import CongestionNotification from "./CongestionNotification.jsx";
import DataAvailabilityNotice from "./DataAvailabilityNotice.jsx";
import GoogleMapPreview from "./GoogleMapPreview.jsx";
import Header from "./Header.jsx";
import JourneyForm from "./JourneyForm.jsx";
import LoadingState from "./LoadingState.jsx";
import RouteList from "./RouteList.jsx";

export default function RoutePlannerPage() {
  const [routes, setRoutes] = useState([]);
  const [recommendedRouteIdentifier, setRecommendedRouteIdentifier] = useState(null);
  const [selectedRouteIdentifier, setSelectedRouteIdentifier] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [thresholdMessage, setThresholdMessage] = useState("");
  const [allRoutesHigh, setAllRoutesHigh] = useState(false);
  const [alternativeDismissed, setAlternativeDismissed] = useState(false);
  const alternativePanelRef = useRef(null);
  const selectedRoute = routes.find((route) => route.route_identifier === selectedRouteIdentifier) || null;
  const {
    congestion,
    updating,
    refreshError,
    notification,
    dismissNotification,
    lastCheckedAt,
  } = useCongestionPolling(selectedRoute?.route_id || null);

  useEffect(() => {
    if (!congestion) return;
    setRoutes((currentRoutes) => currentRoutes.map((route) => (
      route.route_id === congestion.route_id
        ? {
          ...route,
          sensory_score: congestion.sensory_score,
          sensory_indicator: congestion.sensory_indicator,
          threshold_exceeded: congestion.threshold_exceeded,
          data_freshness: congestion.data_freshness,
          updated_at: congestion.updated_at,
          route_segments: congestion.route_segments,
          warning_message: congestion.warning_messages?.join(" ") || route.warning_message,
        }
        : route
    )));
  }, [congestion]);

  const alternatives = useMemo(() => {
    if (!selectedRoute?.threshold_exceeded) return [];
    if (congestion?.route_id === selectedRoute.route_id && congestion.alternatives?.length) {
      return congestion.alternatives;
    }
    return routes
      .filter((route) => route.route_identifier !== selectedRoute.route_identifier && route.qualifies_preference)
      .map((route) => ({
        route_id: route.route_id,
        route_identifier: route.route_identifier,
        sensory_score: route.sensory_score,
        sensory_indicator: route.sensory_indicator,
        estimated_travel_minutes: route.estimated_travel_minutes,
        threshold_exceeded: Boolean(route.threshold_exceeded),
        recommendation_explanation: route.recommendation_explanation,
      }));
  }, [congestion, routes, selectedRoute]);

  function handleSelectRoute(identifier) {
    setSelectedRouteIdentifier(identifier);
    setAlternativeDismissed(false);
  }

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
      setThresholdMessage(response.threshold_message || "");
      setAllRoutesHigh(Boolean(response.all_routes_high));
      setAlternativeDismissed(false);
    } catch (requestError) {
      setRoutes([]);
      setRecommendedRouteIdentifier(null);
      setSelectedRouteIdentifier(null);
      setThresholdMessage("");
      setAllRoutesHigh(false);
      setError(requestError.message || "Unable to generate routes right now.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <Header />
      <main className="planner-page" id="main-content">
        <section className="journey-panel glass-panel" aria-labelledby="journey-heading">
          <div className="panel-heading journey-panel__heading">
            <div>
              <p className="section-kicker">Journey planner</p>
              <h1 id="journey-heading">Plan a calmer journey</h1>
              <p>Compare available routes using travel time and pedestrian-density information.</p>
            </div>
            <span className="location-chip"><span aria-hidden="true">⌖</span> Melbourne CBD</span>
          </div>
          <JourneyForm onSubmit={handleSubmit} loading={loading} />
        </section>

        <div className="status-region" aria-live="polite" aria-atomic="true">
          {error ? <div className="error-state" role="alert"><strong>We couldn’t find routes.</strong><span>{error}</span></div> : null}
          {loading ? <LoadingState /> : null}
          {!loading && routes.length > 0 ? (
            <span className="sr-only">{routes.length} route{routes.length === 1 ? "" : "s"} found.</span>
          ) : null}
        </div>

        {!loading && routes.length > 0 && !recommendedRouteIdentifier ? (
          <p className="recommendation-summary" role="note">
            Sensory-aware recommendation cannot be confirmed because all available routes lack sufficient pedestrian data.
          </p>
        ) : null}

        {!loading && allRoutesHigh ? (
          <p className="recommendation-summary recommendation-summary--high" role="note">
            All available routes contain high-congestion segments. The lowest-impact option remains marked as recommended.
          </p>
        ) : null}

        <CongestionNotification
          notification={notification}
          onDismiss={dismissNotification}
          onReviewAlternative={() => alternativePanelRef.current?.focus()}
        />

        {selectedRoute?.route_id ? (
          <div className="refresh-status" role="status" aria-live="polite">
            <span>{updating ? "Updating congestion..." : "Congestion monitoring active"}</span>
            {lastCheckedAt ? <span>Last checked {lastCheckedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span> : null}
            {refreshError ? <span className="refresh-status__error">{refreshError} Last valid information remains visible.</span> : null}
          </div>
        ) : null}

        {!loading && selectedRoute?.threshold_exceeded && !alternativeDismissed ? (
          <AlternativeRoutePanel
            alternatives={alternatives}
            noAlternativeMessage={alternatives.length ? "" : (thresholdMessage || "No route satisfies the selected threshold; keep the lowest-impact available route.")}
            onKeepCurrent={() => setAlternativeDismissed(true)}
            onSelectAlternative={(alternative) => handleSelectRoute(
              routes.find((route) => route.route_id === alternative.route_id)?.route_identifier || alternative.route_identifier,
            )}
            panelRef={alternativePanelRef}
          />
        ) : null}

        <section className="results-grid" aria-label="Journey results">
          <RouteList
            routes={loading ? [] : routes}
            selectedRouteIdentifier={selectedRouteIdentifier}
            onSelectRoute={handleSelectRoute}
          />
          <GoogleMapPreview
            routes={loading ? [] : routes}
            selectedRouteIdentifier={selectedRouteIdentifier}
            onSelectRoute={handleSelectRoute}
          />
        </section>

        {!loading ? <DataAvailabilityNotice routes={routes} /> : null}
      </main>

      <footer className="site-footer" id="about">
        <p><strong>eScape</strong> · Sensory-aware navigation for Melbourne CBD</p>
        <p>Route information is an aid for comparison. Check current travel conditions before you leave.</p>
      </footer>
    </div>
  );
}
