import {
  API_BASE_URL,
  PREDICTIONS_URL,
  PREDICTIVE_ALERTS_URL,
  REFUGES_URL,
  ROUTE_PLANNING_URL,
  refugeDetailsUrl,
  routeCongestionUrl,
} from "../config/api.js";

function validationMessage(detail) {
  if (!Array.isArray(detail)) return null;

  const messages = detail
    .map((item) => (typeof item === "string" ? item : item?.msg))
    .filter(Boolean);
  return messages.length ? messages.join(" ") : null;
}

function responseErrorMessage(response, payload) {
  const detail = typeof payload?.detail === "string"
    ? payload.detail
    : validationMessage(payload?.detail);
  const message = typeof payload?.message === "string" ? payload.message : null;

  if (response.status === 422) return detail || message || "The backend rejected the journey details. Check the origin, destination, and travel mode.";
  if (response.status === 404) return detail || message || "The local route-planning endpoint was not found.";
  if (response.status === 502) return detail || message || "The external route provider is unavailable.";
  if (response.status === 503) return detail || message || "The local backend is temporarily unavailable. Check its database and external-service configuration.";
  if (response.status >= 500) return "The local backend encountered an error while planning the route.";
  if (detail || message) return detail || message;
  return `Route request failed with status ${response.status}.`;
}

export async function planRoute(payload) {
  let response;
  try {
    response = await fetch(ROUTE_PLANNING_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(`Unable to connect to the local backend. Confirm FastAPI is running on ${API_BASE_URL}.`);
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(responseErrorMessage(response, data));
  }

  return data;
}

export async function getRouteCongestion(routeId, { signal } = {}) {
  let response;
  try {
    response = await fetch(routeCongestionUrl(routeId), {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new Error(`Unable to refresh congestion. Confirm FastAPI is running on ${API_BASE_URL}.`);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(responseErrorMessage(response, data));
  return data;
}

function queryUrl(baseUrl, parameters) {
  const query = new globalThis.URLSearchParams();
  Object.entries(parameters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  });
  return `${baseUrl}?${query.toString()}`;
}

async function getJson(url, { signal, unavailableMessage } = {}) {
  let response;
  try {
    response = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, signal });
  } catch (error) {
    if (error?.name === "AbortError") throw error;
    throw new Error(`Unable to connect to the local backend. Confirm FastAPI is running on ${API_BASE_URL}.`);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : null;
    throw new Error(detail || unavailableMessage || responseErrorMessage(response, data));
  }
  return data;
}

export function searchRefuges(parameters, options = {}) {
  return getJson(queryUrl(REFUGES_URL, parameters), {
    ...options,
    unavailableMessage: "Refuge data is temporarily unavailable.",
  });
}

export function getRefugeDetails(refugeId, parameters = {}, options = {}) {
  return getJson(queryUrl(refugeDetailsUrl(refugeId), parameters), options);
}

export function getPredictions(parameters, options = {}) {
  return getJson(queryUrl(PREDICTIONS_URL, parameters), {
    ...options,
    unavailableMessage: "Prediction services are temporarily unavailable.",
  });
}

export function getPredictiveAlerts(parameters, options = {}) {
  return getJson(queryUrl(PREDICTIVE_ALERTS_URL, parameters), {
    ...options,
    unavailableMessage: "Prediction services are temporarily unavailable.",
  });
}
