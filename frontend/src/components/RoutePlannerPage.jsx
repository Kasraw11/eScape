"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useJourney } from "../context/JourneyContext.jsx";
import { planRoute } from "../services/api.js";
import useCongestionPolling from "../hooks/useCongestionPolling.js";
import AlternativeRoutePanel from "./AlternativeRoutePanel.jsx";
import CongestionNotification from "./CongestionNotification.jsx";
import CurrentTrip from "./CurrentTrip.jsx";
import DataAvailabilityNotice from "./DataAvailabilityNotice.jsx";
import GoogleMapPreview from "./GoogleMapPreview.jsx";
import JourneyForm from "./JourneyForm.jsx";
import LoadingState from "./LoadingState.jsx";
import PlanPageTabs from "./PlanPageTabs.jsx";
import RouteList from "./RouteList.jsx";

export default function RoutePlannerPage() {
  const { activeJourney, startJourney, endJourney } = useJourney();
  const [activeTab, setActiveTab] = useState("journey");
  const [routes, setRoutes] = useState([]);
  const [journeyDetails, setJourneyDetails] = useState(null);
  const [recommendedRouteIdentifier, setRecommendedRouteIdentifier] = useState(null);
  const [selectedRouteIdentifier, setSelectedRouteIdentifier] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [thresholdMessage, setThresholdMessage] = useState("");
  const [allRoutesHigh, setAllRoutesHigh] = useState(false);
  const [alternativeDismissed, setAlternativeDismissed] = useState(false);
  const [tripNotice, setTripNotice] = useState("");
  const alternativePanelRef = useRef(null);
  const selectedRoute = routes.find((route) => route.route_identifier === selectedRouteIdentifier) || null;
  const polling = useCongestionPolling(activeJourney?.route?.route_id || null);

  useEffect(() => {
    if (!polling.congestion) return;
    setRoutes((current) => current.map((route) => route.route_id === polling.congestion.route_id ? { ...route, sensory_score: polling.congestion.sensory_score, sensory_indicator: polling.congestion.sensory_indicator, threshold_exceeded: polling.congestion.threshold_exceeded, data_freshness: polling.congestion.data_freshness, updated_at: polling.congestion.updated_at, route_segments: polling.congestion.route_segments } : route));
  }, [polling.congestion]);

  const alternatives = useMemo(() => selectedRoute?.threshold_exceeded ? routes.filter((route) => route.route_identifier !== selectedRoute.route_identifier && route.qualifies_preference) : [], [routes, selectedRoute]);

  async function handleSubmit(payload, details) {
    setLoading(true); setError(""); setTripNotice("");
    try {
      const response = await planRoute(payload); const nextRoutes = response.routes || []; const recommended = response.recommended_route_identifier || null;
      setRoutes(nextRoutes); setJourneyDetails(details); setRecommendedRouteIdentifier(recommended); setSelectedRouteIdentifier(null); setThresholdMessage(response.threshold_message || ""); setAllRoutesHigh(Boolean(response.all_routes_high)); setAlternativeDismissed(false);
    } catch (requestError) { setRoutes([]); setJourneyDetails(null); setRecommendedRouteIdentifier(null); setSelectedRouteIdentifier(null); setError(requestError.message || "Unable to generate routes right now."); }
    finally { setLoading(false); }
  }

  function selectRoute(identifier) { setSelectedRouteIdentifier(identifier); setTripNotice(""); setAlternativeDismissed(false); }
  function handleStartTrip() { if (!selectedRoute || !journeyDetails) return; startJourney({ ...journeyDetails, route: selectedRoute, startedAt: new Date().toISOString() }); setTripNotice("Trip started. Current Trip is ready when you want to open it."); }

  return <div className="plan-page page-stack"><header className="page-heading"><p className="section-kicker">Melbourne CBD</p><h1>Plan a calmer journey</h1><p>Compare routes, choose one, then explicitly start your trip.</p></header><PlanPageTabs activeTab={activeTab} onChange={setActiveTab} />
    <section id="plan-panel-journey" role="tabpanel" aria-labelledby="plan-tab-journey" hidden={activeTab !== "journey"}>
      <section className="journey-panel glass-panel" aria-labelledby="journey-heading"><div className="panel-heading journey-panel__heading"><div><p className="section-kicker">Plan Journey</p><h2 id="journey-heading">Where would you like to go?</h2><p>Type an address, landmark, place, or Melbourne CBD location.</p></div><span className="location-chip">Melbourne CBD</span></div><JourneyForm onSubmit={handleSubmit} loading={loading} /></section>
      <div className="status-region" aria-live="polite" aria-atomic="true">{error ? <div className="error-state" role="alert"><strong>We couldn’t find routes.</strong><span>{error}</span></div> : null}{loading ? <LoadingState /> : null}{tripNotice ? <p className="success-notice" role="status">{tripNotice} <button type="button" onClick={() => setActiveTab("trip")}>Open Current Trip</button></p> : null}</div>
      {!loading && routes.length > 0 && !recommendedRouteIdentifier ? <p className="recommendation-summary" role="note">Sensory-aware recommendation cannot be confirmed because all available routes lack sufficient pedestrian data.</p> : null}{!loading && allRoutesHigh ? <p className="recommendation-summary recommendation-summary--high" role="note">All available routes contain high-congestion segments. The lowest-impact option remains marked as recommended.</p> : null}
      <CongestionNotification notification={polling.notification} onDismiss={polling.dismissNotification} onReviewAlternative={() => { setActiveTab("journey"); alternativePanelRef.current?.focus(); }} />
      {!loading && selectedRoute?.threshold_exceeded && !alternativeDismissed ? <AlternativeRoutePanel alternatives={alternatives} noAlternativeMessage={alternatives.length ? "" : (thresholdMessage || "No route satisfies the selected threshold.")} onKeepCurrent={() => setAlternativeDismissed(true)} onSelectAlternative={(alternative) => selectRoute(alternative.route_identifier)} panelRef={alternativePanelRef} /> : null}
      <section className="results-grid" aria-label="Journey results"><RouteList routes={loading ? [] : routes} selectedRouteIdentifier={selectedRouteIdentifier} onSelectRoute={selectRoute} /><GoogleMapPreview routes={loading ? [] : routes} selectedRouteIdentifier={selectedRouteIdentifier} onSelectRoute={selectRoute} /></section>
      {selectedRoute && journeyDetails ? <div className="start-trip-bar"><div><strong>{selectedRoute.route_identifier} selected</strong><span>Selecting a route does not start your trip.</span></div><button className="primary-button" type="button" onClick={handleStartTrip}>Start Trip</button></div> : null}{!loading ? <DataAvailabilityNotice routes={routes} /> : null}
    </section>
    <section id="plan-panel-trip" role="tabpanel" aria-labelledby="plan-tab-trip" hidden={activeTab !== "trip"}><CurrentTrip journey={activeJourney} congestion={polling.congestion} lastCheckedAt={polling.lastCheckedAt} updating={polling.updating} refreshError={polling.refreshError} onPlan={() => setActiveTab("journey")} onEnd={() => { endJourney(); setTripNotice(""); }} /></section>
  </div>;
}
