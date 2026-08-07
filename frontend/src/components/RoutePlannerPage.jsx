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
import JourneyFeedback from "./JourneyFeedback.jsx";
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
  const [alternativeOpen, setAlternativeOpen] = useState(false);
  const [tripNotice, setTripNotice] = useState("");
  const [feedbackJourney, setFeedbackJourney] = useState(null);
  const alternativeReturnRef = useRef(null);
  const selectedRoute = routes.find((route) => route.route_identifier === selectedRouteIdentifier) || null;
  const polling = useCongestionPolling(activeJourney?.route?.route_id || null);

  useEffect(() => {
    if (!polling.congestion) return;
    setRoutes((current) => current.map((route) => route.route_id === polling.congestion.route_id ? { ...route, sensory_score: polling.congestion.sensory_score, sensory_indicator: polling.congestion.sensory_indicator, threshold_exceeded: polling.congestion.threshold_exceeded, data_freshness: polling.congestion.data_freshness, updated_at: polling.congestion.updated_at, route_segments: polling.congestion.route_segments } : route));
  }, [polling.congestion]);

  const alternatives = useMemo(() => selectedRoute?.threshold_exceeded ? routes.filter((route) => route.route_identifier !== selectedRoute.route_identifier && route.qualifies_preference) : [], [routes, selectedRoute]);

  async function handleSubmit(payload, details) {
    setLoading(true); setError(""); setTripNotice(""); setAlternativeOpen(false);
    try {
      const response = await planRoute(payload);
      setRoutes(response.routes || []); setJourneyDetails(details); setRecommendedRouteIdentifier(response.recommended_route_identifier || null); setSelectedRouteIdentifier(null); setThresholdMessage(response.threshold_message || ""); setAllRoutesHigh(Boolean(response.all_routes_high));
    } catch (requestError) {
      setRoutes([]); setJourneyDetails(null); setRecommendedRouteIdentifier(null); setSelectedRouteIdentifier(null); setError(requestError.message || "Unable to generate routes right now.");
    } finally { setLoading(false); }
  }

  function selectRoute(identifier) {
    const route = routes.find((item) => item.route_identifier === identifier);
    setSelectedRouteIdentifier(identifier); setTripNotice("");
    setAlternativeOpen(Boolean(route?.threshold_exceeded));
  }

  function handleStartTrip(identifier = selectedRouteIdentifier) {
    const routeToStart = routes.find((route) => route.route_identifier === identifier);
    if (!routeToStart || !journeyDetails) return;
    setSelectedRouteIdentifier(identifier);
    startJourney({ ...journeyDetails, route: routeToStart, startedAt: new Date().toISOString() });
    setTripNotice("Trip started. Current trip is active.");
    setActiveTab("trip");
  }

  function handleEndJourney() {
    setFeedbackJourney(activeJourney);
    endJourney();
    setTripNotice("");
    setActiveTab("journey");
  }

  return <div className="plan-page page-stack"><PlanPageTabs activeTab={activeTab} onChange={setActiveTab} />
    {tripNotice ? <p className="sr-only" role="status">{tripNotice}</p> : null}
    <section id="plan-panel-journey" role="tabpanel" aria-labelledby="plan-tab-journey" hidden={activeTab !== "journey"}>
      <div className="status-region" aria-live="polite" aria-atomic="true">{error ? <div className="error-state" role="alert"><strong>We couldn’t find routes.</strong><span>{error}</span></div> : null}{loading ? <LoadingState /> : null}<span className="sr-only">{!loading && routes.length ? `${routes.length} route options available.` : ""}</span></div>
      {!loading && routes.length > 0 && !recommendedRouteIdentifier ? <p className="recommendation-summary" role="note">Sensory-aware recommendation cannot be confirmed because crowd information is unavailable.</p> : null}{!loading && allRoutesHigh ? <p className="recommendation-summary recommendation-summary--high" role="note">All available routes contain high-congestion segments. The lowest-impact option is marked as recommended.</p> : null}
      <div className="plan-workspace">
        <section className="journey-panel glass-panel" aria-labelledby="journey-heading"><div className="journey-panel__heading"><h1 id="journey-heading">Plan your journey</h1><p>Compare calmer routes and start only when you&apos;re ready.</p></div><JourneyForm onSubmit={handleSubmit} loading={loading} /></section>
        <div className="route-visual-column">
          <GoogleMapPreview routes={loading ? [] : routes} selectedRouteIdentifier={selectedRouteIdentifier} onSelectRoute={selectRoute} />
          <RouteList routes={loading ? [] : routes} selectedRouteIdentifier={selectedRouteIdentifier} onSelectRoute={selectRoute} onStartJourney={journeyDetails ? handleStartTrip : undefined} />
          {!loading ? <DataAvailabilityNotice routes={routes} /> : null}
        </div>
      </div>
      <AlternativeRoutePanel open={alternativeOpen} currentRoute={selectedRoute} alternatives={alternatives} noAlternativeMessage={alternatives.length ? "" : (thresholdMessage || "No route meets your selected crowd tolerance.")} onKeepCurrent={() => setAlternativeOpen(false)} onSelectAlternative={(alternative) => { selectRoute(alternative.route_identifier); setAlternativeOpen(false); }} returnFocusRef={alternativeReturnRef} />
    </section>
    <section id="plan-panel-trip" role="tabpanel" aria-labelledby="plan-tab-trip" hidden={activeTab !== "trip"}><CongestionNotification notification={polling.notification} onDismiss={polling.dismissNotification} onReviewAlternative={() => { setActiveTab("journey"); setAlternativeOpen(true); }} /><CurrentTrip journey={activeJourney} congestion={polling.congestion} lastCheckedAt={polling.lastCheckedAt} updating={polling.updating} refreshError={polling.refreshError} onPlan={() => setActiveTab("journey")} onEnd={handleEndJourney} /></section>
    <JourneyFeedback open={Boolean(feedbackJourney)} journey={feedbackJourney} onClose={() => setFeedbackJourney(null)} />
  </div>;
}
