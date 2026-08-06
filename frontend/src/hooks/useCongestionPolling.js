"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { CONGESTION_POLL_INTERVAL_MS } from "../config/api.js";
import { getRouteCongestion } from "../services/api.js";


export default function useCongestionPolling(routeId, { intervalMs = CONGESTION_POLL_INTERVAL_MS } = {}) {
  const [congestion, setCongestion] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [refreshError, setRefreshError] = useState("");
  const [notification, setNotification] = useState(null);
  const [lastCheckedAt, setLastCheckedAt] = useState(null);
  const requestInFlightRef = useRef(false);
  const activeControllerRef = useRef(null);
  const lastNotificationKeyRef = useRef(null);

  const dismissNotification = useCallback(() => setNotification(null), []);

  useEffect(() => {
    setCongestion(null);
    setRefreshError("");
    setNotification(null);
    lastNotificationKeyRef.current = null;
    if (!routeId) return undefined;

    let active = true;
    let timerId;
    let controller;

    const schedule = () => {
      if (active) timerId = window.setTimeout(refresh, intervalMs);
    };

    async function refresh() {
      window.clearTimeout(timerId);
      if (!active) return;
      if (requestInFlightRef.current) {
        schedule();
        return;
      }
      if (window.navigator.onLine === false) {
        setRefreshError("Congestion refresh is paused while the browser is offline.");
        schedule();
        return;
      }
      if (typeof document !== "undefined" && document.visibilityState === "hidden") {
        schedule();
        return;
      }

      requestInFlightRef.current = true;
      controller = new window.AbortController();
      const requestController = controller;
      activeControllerRef.current = requestController;
      setUpdating(true);
      try {
        const nextCongestion = await getRouteCongestion(routeId, { signal: controller.signal });
        if (!active) return;
        setCongestion(nextCongestion);
        setRefreshError("");
        setLastCheckedAt(new Date());
        const nextNotification = nextCongestion.meaningful_change ? nextCongestion.notification : null;
        if (nextNotification?.change_key && nextNotification.change_key !== lastNotificationKeyRef.current) {
          lastNotificationKeyRef.current = nextNotification.change_key;
          setNotification(nextNotification);
        }
      } catch (error) {
        if (active && error?.name !== "AbortError") {
          setRefreshError(error.message || "Current congestion could not be refreshed. The last valid update is still shown.");
        }
      } finally {
        if (activeControllerRef.current === requestController) {
          requestInFlightRef.current = false;
          activeControllerRef.current = null;
        }
        if (active) {
          setUpdating(false);
          schedule();
        }
      }
    }

    const resumeWhenVisible = () => {
      if (document.visibilityState === "visible") refresh();
    };
    const resumeWhenOnline = () => refresh();

    refresh();
    document.addEventListener("visibilitychange", resumeWhenVisible);
    window.addEventListener("online", resumeWhenOnline);
    return () => {
      active = false;
      window.clearTimeout(timerId);
      controller?.abort();
      if (activeControllerRef.current === controller) {
        requestInFlightRef.current = false;
        activeControllerRef.current = null;
      }
      document.removeEventListener("visibilitychange", resumeWhenVisible);
      window.removeEventListener("online", resumeWhenOnline);
    };
  }, [intervalMs, routeId]);

  return {
    congestion,
    updating,
    refreshError,
    notification,
    dismissNotification,
    lastCheckedAt,
  };
}
