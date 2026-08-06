"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getPredictions, getPredictiveAlerts } from "../services/api.js";
import PointMapPanel from "./PointMapPanel.jsx";

const CBD = { latitude: -37.8136, longitude: 144.9631 };
const POLL_INTERVAL_MS = 90_000;

function formatTime(value) {
  return new Intl.DateTimeFormat("en-AU", { hour: "numeric", minute: "2-digit", timeZone: "Australia/Melbourne" }).format(new Date(value));
}

function timelineSection(value) {
  const minutes = (new Date(value).getTime() - Date.now()) / 60_000;
  if (minutes <= 10) return "Now";
  if (minutes <= 30) return "Next 30 minutes";
  return "Next hour";
}

function deduplicateAlerts(alerts) {
  const byKey = new Map();
  alerts.forEach((alert) => {
    const key = alert.deduplication_key || String(alert.alert_id);
    const existing = byKey.get(key);
    if (!existing || new Date(alert.updated_at) > new Date(existing.updated_at)) byKey.set(key, alert);
  });
  return [...byKey.values()].sort((first, second) => new Date(first.predicted_time) - new Date(second.predicted_time));
}

export { deduplicateAlerts };

export default function AlertsPage() {
  const [preferences, setPreferences] = useState({ enabled: true, minimumSeverity: "high", maximumDistance: 1000, routeOnly: false });
  const [predictions, setPredictions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [dismissed, setDismissed] = useState(new Set());
  const [selectedId, setSelectedId] = useState(null);
  const [serviceAvailable, setServiceAvailable] = useState(true);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshToken, setRefreshToken] = useState(0);

  const load = useCallback(async (signal) => {
    const predictionRequest = getPredictions({
      ...CBD,
      radius_m: preferences.maximumDistance,
      forecast_minutes: 60,
      minimum_severity: "low",
    }, { signal });
    const alertRequest = getPredictiveAlerts({
      ...CBD,
      enabled: preferences.enabled,
      minimum_severity: preferences.minimumSeverity,
      maximum_distance_m: preferences.maximumDistance,
      route_only: preferences.routeOnly,
    }, { signal });
    const [predictionResult, alertResult] = await Promise.allSettled([predictionRequest, alertRequest]);
    if (signal.aborted) return;
    if (predictionResult.status === "fulfilled") {
      setPredictions(predictionResult.value.predictions || []);
      setServiceAvailable(Boolean(predictionResult.value.service_available));
      setMessage(predictionResult.value.message || "");
    } else {
      setPredictions([]);
      setServiceAvailable(false);
      setMessage(predictionResult.reason?.message || "Prediction services are temporarily unavailable.");
    }
    if (alertResult.status === "fulfilled") setAlerts(deduplicateAlerts(alertResult.value.alerts || []));
    else setAlerts([]);
    setLastUpdated(new Date());
    setLoading(false);
  }, [preferences]);

  useEffect(() => {
    let timer;
    let controller;
    let stopped = false;
    async function tick() {
      if (stopped) return;
      if (document.visibilityState !== "hidden" && globalThis.navigator.onLine !== false) {
        controller = new globalThis.AbortController();
        await load(controller.signal);
      }
      if (!stopped) timer = window.setTimeout(tick, POLL_INTERVAL_MS);
    }
    setLoading(true);
    tick();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      controller?.abort();
    };
  }, [load, refreshToken]);

  const visibleAlerts = useMemo(
    () => deduplicateAlerts(alerts).filter((alert) => !dismissed.has(alert.deduplication_key || String(alert.alert_id))),
    [alerts, dismissed],
  );
  const sections = useMemo(() => ["Now", "Next 30 minutes", "Next hour"].map((title) => ({
    title,
    alerts: visibleAlerts.filter((alert) => timelineSection(alert.predicted_time) === title),
  })), [visibleAlerts]);
  const highPredictions = useMemo(() => predictions.filter((prediction) => prediction.severity === "High"), [predictions]);
  const mapPoints = useMemo(() => highPredictions.map((prediction) => ({
    id: prediction.prediction_id,
    name: prediction.location_name,
    latitude: prediction.latitude,
    longitude: prediction.longitude,
    status: prediction.severity,
    confidence: prediction.confidence,
  })), [highPredictions]);

  function updatePreference(field, value) {
    setPreferences((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="iteration-page page-stack alerts-app">
        <section className="iteration-hero glass-panel">
          <p className="section-kicker">Next-hour crowd forecast</p>
          <h1>Plan around likely crowded areas</h1>
          <p>Predictions are deterministic estimates from current counts, recent trend, and the matching City of Melbourne weekday/hour history. They are not guarantees.</p>
        </section>

        <section className="control-panel glass-panel" aria-labelledby="alert-preferences-heading">
          <div className="results-heading"><div><h2 id="alert-preferences-heading">Predictive alert preferences</h2><p>These settings are temporary for this browser page and are filtered by the backend.</p></div><button type="button" onClick={() => setRefreshToken((value) => value + 1)}>Refresh predictions</button></div>
          <div className="preference-grid">
            <label className="checkbox-control"><input type="checkbox" checked={preferences.enabled} onChange={(event) => updatePreference("enabled", event.target.checked)} /> Enable predictive alerts</label>
            <label>Minimum severity<select aria-label="Minimum severity" value={preferences.minimumSeverity} onChange={(event) => updatePreference("minimumSeverity", event.target.value)}><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option></select></label>
            <label>Maximum alert distance<select aria-label="Maximum alert distance" value={preferences.maximumDistance} onChange={(event) => updatePreference("maximumDistance", Number(event.target.value))}><option value="500">500 metres</option><option value="1000">1 kilometre</option><option value="2000">2 kilometres</option><option value="5000">5 kilometres</option></select></label>
            <label className="checkbox-control"><input type="checkbox" checked={preferences.routeOnly} onChange={(event) => updatePreference("routeOnly", event.target.checked)} /> Only when selected route is affected</label>
          </div>
        </section>

        <div className="prediction-status" aria-live="polite">
          {loading ? <p>Loading next-hour predictions…</p> : null}
          {!loading && !serviceAvailable ? <p className="error-state" role="alert">Prediction services are temporarily unavailable.</p> : null}
          {!loading && serviceAvailable ? <p>{visibleAlerts.length} matching predictive alert{visibleAlerts.length === 1 ? "" : "s"}. {lastUpdated ? `Last updated ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}.` : ""}</p> : null}
          {message && serviceAvailable ? <p>{message}</p> : null}
        </div>

        <div className="iteration-grid alerts-grid">
          <section className="alert-timeline glass-panel" aria-labelledby="alert-timeline-heading">
            <p className="section-kicker">Simple timeline</p><h2 id="alert-timeline-heading">Predictive alerts</h2>
            {!loading && serviceAvailable && visibleAlerts.length === 0 ? <div className="empty-state"><h3>No matching active alerts</h3><p>No validated high-crowd forecast currently matches these preferences.</p></div> : null}
            {sections.map((section) => <section className="timeline-section" key={section.title} aria-labelledby={`timeline-${section.title.replaceAll(" ", "-")}`}>
              <h3 id={`timeline-${section.title.replaceAll(" ", "-")}`}>{section.title}</h3>
              {section.alerts.map((alert) => <article className="predictive-alert-card" key={alert.deduplication_key || alert.alert_id}>
                <div className="card-title-row"><div><span className={`severity-badge severity-badge--${alert.severity.toLowerCase()}`}>{alert.severity}</span><h4>{alert.location_name}</h4></div><strong>{formatTime(alert.predicted_time)}</strong></div>
                <p><strong>{alert.confidence} confidence</strong> · {alert.data_freshness} source data</p>
                <p>{alert.route_impact}</p><p>{alert.message}</p>
                <p className="updated-copy">Last updated {formatTime(alert.updated_at)}</p>
                <div className="card-actions">
                  <button type="button" onClick={() => setSelectedId(alert.prediction_id)}>View on map</button>
                  <Link href="/plan">Review alternative</Link>
                  <button type="button" onClick={() => setDismissed((current) => new Set(current).add(alert.deduplication_key || String(alert.alert_id)))}>Dismiss</button>
                </div>
              </article>)}
            </section>)}
          </section>
          <PointMapPanel
            title="Predicted high-crowd areas"
            points={mapPoints}
            selectedId={selectedId}
            onSelect={setSelectedId}
            label="Next-hour predicted high-crowd area map"
            legend="Red marker High predicted severity. Every marker also has a text label and confidence value."
          />
        </div>

        <section className="method-panel glass-panel" aria-labelledby="prediction-method-heading">
          <h2 id="prediction-method-heading">How to read this forecast</h2>
          <p>Low-confidence estimates are explicitly labelled. Missing historical or current data is shown as unavailable, not converted into a Low forecast. Weather, events and unexpected sensor outages are not modelled.</p>
        </section>
    </div>
  );
}
