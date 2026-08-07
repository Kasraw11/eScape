"use client";

import Link from "next/link";
import GoogleMapPreview from "./GoogleMapPreview.jsx";
import SensoryIndicator from "./SensoryIndicator.jsx";

function arrival(minutes) {
  const date = new Date(Date.now() + Number(minutes || 0) * 60000);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function distance(route) {
  const metres = (route.route_segments || []).reduce((total, segment) => total + Number(segment.distance_m || 0), 0);
  if (!metres) return null;
  return metres >= 1000 ? `${(metres / 1000).toFixed(1)} km` : `${Math.round(metres)} m`;
}

export default function CurrentTrip({ journey, congestion, lastCheckedAt, updating, refreshError, onPlan, onEnd }) {
  if (!journey) return <section className="current-trip-empty glass-panel"><h1>No active trip</h1><p>Start a route from Plan your journey and it will appear here.</p><button className="primary-button" type="button" onClick={onPlan}>Plan a journey</button></section>;
  const route = congestion ? { ...journey.route, sensory_score: congestion.sensory_score, sensory_indicator: congestion.sensory_indicator, threshold_exceeded: congestion.threshold_exceeded, data_freshness: congestion.data_freshness, updated_at: congestion.updated_at, route_segments: congestion.route_segments } : journey.route;
  const nextSegment = route.route_segments?.[0];
  return (
    <div className="current-trip-layout">
      <section className="current-trip-card glass-panel"><div className="current-trip-card__heading"><div><p className="section-kicker">Current trip</p><h1>{journey.destination.label}</h1></div><span className="status-badge">In progress</span></div><p className="trip-route-copy"><span>{journey.origin.formattedAddress || journey.origin.label}</span><span aria-hidden="true">→</span><span>{journey.destination.formattedAddress || journey.destination.label}</span></p><dl className="trip-metrics"><div><dt>Time remaining</dt><dd>{route.estimated_travel_minutes} min</dd></div>{distance(route) ? <div><dt>Distance</dt><dd>{distance(route)}</dd></div> : null}<div><dt>Estimated arrival</dt><dd>{arrival(route.estimated_travel_minutes)}</dd></div><div><dt>Sensory condition</dt><dd><SensoryIndicator indicator={route.sensory_indicator} /></dd></div><div><dt>Last update</dt><dd>{lastCheckedAt ? lastCheckedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Waiting for update"}</dd></div><div><dt>Data</dt><dd>{route.data_freshness || "Unavailable"}</dd></div></dl>{nextSegment?.instruction ? <div className="trip-next-step"><span>Next</span><strong>{nextSegment.instruction}</strong>{nextSegment.distance_m ? <small>{nextSegment.distance_m} m</small> : null}</div> : null}{updating ? <p role="status">Updating congestion…</p> : null}{refreshError ? <p className="field-error">{refreshError} Last valid information remains visible.</p> : null}<div className="trip-actions"><button type="button" onClick={onPlan}>Review route options</button><Link href="/refuges">Find refuge nearby</Link><button className="danger-button" type="button" onClick={onEnd}>End trip</button></div></section>
      <GoogleMapPreview routes={[route]} selectedRouteIdentifier={route.route_identifier} />
    </div>
  );
}
