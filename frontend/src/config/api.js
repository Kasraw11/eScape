const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function normalizeApiBaseUrl(value) {
  const configuredApiUrl = value?.trim();
  return configuredApiUrl?.replace(/\/+$/, "") || DEFAULT_API_BASE_URL;
}

export const API_BASE_URL = normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
export const ROUTE_PLANNING_URL = `${API_BASE_URL}/api/routes/plan`;
export const REFUGES_URL = `${API_BASE_URL}/api/refuges`;
export const PREDICTIONS_URL = `${API_BASE_URL}/api/predictions`;
export const PREDICTIVE_ALERTS_URL = `${API_BASE_URL}/api/alerts/predictive`;

export function routeCongestionUrl(routeId) {
  return `${API_BASE_URL}/api/routes/${encodeURIComponent(routeId)}/congestion`;
}

export function refugeDetailsUrl(refugeId) {
  return `${REFUGES_URL}/${encodeURIComponent(refugeId)}`;
}

const configuredPollInterval = Number(process.env.NEXT_PUBLIC_CONGESTION_POLL_INTERVAL_MS);
export const CONGESTION_POLL_INTERVAL_MS = Number.isFinite(configuredPollInterval)
  ? Math.max(60_000, configuredPollInterval)
  : 90_000;
