"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { getPredictiveAlerts } from "../services/api.js";
import { useSettings } from "./SettingsContext.jsx";

const AlertCenterContext = createContext(null);
const CBD = { latitude: -37.8136, longitude: 144.9631 };
const PREDICTIVE_REFRESH_MS = 90_000;

function keyFor(alert) {
  return String(alert.id ?? alert.alert_id ?? alert.deduplication_key);
}

function normalizePredictiveAlert(alert) {
  const id = `predictive:${alert.deduplication_key || alert.alert_id || alert.prediction_id}`;
  const affectsCurrentRoute = Boolean(alert.route_relevant) || /selected route affected/i.test(alert.route_impact || "");
  return {
    id,
    type: "predictive",
    title: alert.severity === "High" ? "High sensory conditions ahead" : "Sensory conditions predicted",
    area: alert.location_name,
    severity: alert.severity,
    stressor: "Crowding",
    message: alert.message,
    timestamp: alert.updated_at || alert.generated_at || alert.predicted_time,
    predictedTime: alert.predicted_time,
    confidence: alert.confidence,
    routeImpact: alert.route_impact,
    latitude: alert.latitude,
    longitude: alert.longitude,
    affectsCurrentRoute,
    // Alternatives are only advertised when the live route response supplies one.
    alternativeAvailable: false,
    active: alert.status !== "closed" && alert.status !== "superseded",
  };
}

function mergeAlert(current, incoming) {
  const changed = current.timestamp !== incoming.timestamp
    || current.message !== incoming.message
    || current.severity !== incoming.severity;
  return {
    ...current,
    ...incoming,
    read: changed ? false : current.read,
    dismissed: changed ? false : current.dismissed,
  };
}

export function AlertCenterProvider({ children }) {
  const { notificationPreferences } = useSettings();
  const [alerts, setAlerts] = useState([]);
  const [selectedAlertId, setSelectedAlertId] = useState(null);

  const upsertAlerts = useCallback((incomingAlerts) => {
    const incoming = (Array.isArray(incomingAlerts) ? incomingAlerts : [incomingAlerts]).filter(Boolean);
    if (!incoming.length) return;
    setAlerts((current) => {
      const byId = new Map(current.map((alert) => [keyFor(alert), alert]));
      incoming.forEach((alert) => {
        const id = keyFor(alert);
        const existing = byId.get(id);
        byId.set(id, existing ? mergeAlert(existing, alert) : { ...alert, id, read: false, dismissed: false });
      });
      return [...byId.values()].sort((first, second) => new Date(second.timestamp || 0) - new Date(first.timestamp || 0));
    });
  }, []);

  const syncPredictiveAlerts = useCallback((incomingAlerts) => {
    const normalized = incomingAlerts.map(normalizePredictiveAlert);
    const activeIds = new Set(normalized.filter((alert) => alert.active).map(keyFor));
    setAlerts((current) => current.map((alert) => alert.type === "predictive" && !activeIds.has(keyFor(alert)) ? { ...alert, active: false } : alert));
    upsertAlerts(normalized);
  }, [upsertAlerts]);

  const resolveAlerts = useCallback((type) => {
    setAlerts((current) => current.map((alert) => alert.type === type && alert.affectsCurrentRoute ? { ...alert, active: false } : alert));
  }, []);
  const deactivateTripAlerts = useCallback(() => {
    setAlerts((current) => current.map((alert) => alert.affectsCurrentRoute ? { ...alert, active: false } : alert));
    setSelectedAlertId(null);
  }, []);
  const dismissTripAlert = useCallback((id) => {
    setAlerts((current) => current.map((alert) => keyFor(alert) === String(id) ? { ...alert, dismissed: true, read: true } : alert));
  }, []);
  const markAllRead = useCallback(() => {
    setAlerts((current) => current.map((alert) => ({ ...alert, read: true })));
  }, []);
  const selectAlert = useCallback((id) => {
    setSelectedAlertId(String(id));
    setAlerts((current) => current.map((alert) => keyFor(alert) === String(id) ? { ...alert, read: true } : alert));
  }, []);

  useEffect(() => {
    if (!notificationPreferences.sensoryAlerts) return undefined;
    let active = true;
    let timer;
    let controller;

    async function refresh() {
      window.clearTimeout(timer);
      if (!active) return;
      controller = new globalThis.AbortController();
      try {
        const response = await getPredictiveAlerts({
          ...CBD,
          enabled: true,
          minimum_severity: "moderate",
          maximum_distance_m: 2000,
          route_only: false,
        }, { signal: controller.signal });
        if (active) syncPredictiveAlerts(response.alerts || []);
      } catch (error) {
        if (error?.name !== "AbortError") {
          // Existing notifications remain available during a temporary refresh failure.
        }
      } finally {
        if (active) timer = window.setTimeout(refresh, PREDICTIVE_REFRESH_MS);
      }
    }

    refresh();
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller?.abort();
    };
  }, [notificationPreferences.sensoryAlerts, syncPredictiveAlerts]);

  const value = useMemo(() => ({
    notifications: alerts,
    tripAlerts: alerts.filter((alert) => alert.active && alert.affectsCurrentRoute && !alert.dismissed),
    selectedAlertId,
    upsertAlert: upsertAlerts,
    resolveAlerts,
    deactivateTripAlerts,
    dismissTripAlert,
    markAllRead,
    selectAlert,
  }), [alerts, deactivateTripAlerts, dismissTripAlert, markAllRead, resolveAlerts, selectAlert, selectedAlertId, upsertAlerts]);

  return <AlertCenterContext.Provider value={value}>{children}</AlertCenterContext.Provider>;
}

export function useAlertCenter() {
  const context = useContext(AlertCenterContext);
  const [fallbackAlerts, setFallbackAlerts] = useState([]);
  const [fallbackSelected, setFallbackSelected] = useState(null);
  const fallbackUpsert = useCallback((alert) => {
    const incoming = Array.isArray(alert) ? alert : [alert];
    setFallbackAlerts((current) => {
      const byId = new Map(current.map((item) => [keyFor(item), item]));
      incoming.filter(Boolean).forEach((item) => {
        const id = keyFor(item);
        byId.set(id, byId.has(id) ? mergeAlert(byId.get(id), item) : { ...item, id, read: false, dismissed: false });
      });
      return [...byId.values()];
    });
  }, []);
  const fallbackResolve = useCallback((type) => { setFallbackAlerts((current) => current.map((alert) => alert.type === type ? { ...alert, active: false } : alert)); }, []);
  const fallbackDeactivate = useCallback(() => { setFallbackAlerts((current) => current.map((alert) => ({ ...alert, active: false }))); setFallbackSelected(null); }, []);
  const fallbackDismiss = useCallback((id) => { setFallbackAlerts((current) => current.map((alert) => keyFor(alert) === String(id) ? { ...alert, dismissed: true, read: true } : alert)); }, []);
  const fallbackMarkRead = useCallback(() => { setFallbackAlerts((current) => current.map((alert) => ({ ...alert, read: true }))); }, []);
  const fallbackSelect = useCallback((id) => { setFallbackSelected(String(id)); setFallbackAlerts((current) => current.map((alert) => keyFor(alert) === String(id) ? { ...alert, read: true } : alert)); }, []);
  const fallback = useMemo(() => ({
    notifications: fallbackAlerts,
    tripAlerts: fallbackAlerts.filter((alert) => alert.active && alert.affectsCurrentRoute && !alert.dismissed),
    selectedAlertId: fallbackSelected,
    upsertAlert: fallbackUpsert,
    resolveAlerts: fallbackResolve,
    deactivateTripAlerts: fallbackDeactivate,
    dismissTripAlert: fallbackDismiss,
    markAllRead: fallbackMarkRead,
    selectAlert: fallbackSelect,
  }), [fallbackAlerts, fallbackDeactivate, fallbackDismiss, fallbackMarkRead, fallbackResolve, fallbackSelect, fallbackSelected, fallbackUpsert]);
  return context || fallback;
}
