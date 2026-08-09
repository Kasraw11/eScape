// Same-origin Next.js proxy; FastAPI remains bound to localhost.
const DEFAULT_API_BASE_URL = "/backend";

/**
 * Normalizes the backend base URL.
 * Removes trailing "/" characters to avoid malformed API URLs.
 */
export function normalizeApiBaseUrl(value) {
  const configuredApiUrl = value?.trim();

  return (
    configuredApiUrl?.replace(/\/+$/, "") ||
    DEFAULT_API_BASE_URL
  );
}

/**
 * Main backend URL.
 * This can be overridden using NEXT_PUBLIC_API_BASE_URL.
 */
export const API_BASE_URL = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL
);

/**
 * Route-planning endpoint.
 * Used by the main journey planner.
 */
export const ROUTE_PLANNING_URL =
  `${API_BASE_URL}/api/routes/plan`;


/* -------------------------------------------------
   Other eScape endpoints
   These can stay for later features.
-------------------------------------------------- */

export const REFUGES_URL =
  `${API_BASE_URL}/api/refuges`;

export const PREDICTIONS_URL =
  `${API_BASE_URL}/api/predictions`;

export const PREDICTIVE_ALERTS_URL =
  `${API_BASE_URL}/api/alerts/predictive`;

export const FEEDBACK_URL =
  `${API_BASE_URL}/api/feedback`;


/**
 * Builds the congestion endpoint for one route.
 */
export function routeCongestionUrl(routeId) {
  return `${API_BASE_URL}/api/routes/${encodeURIComponent(
    routeId
  )}/congestion`;
}


/**
 * Builds the details endpoint for one refuge.
 */
export function refugeDetailsUrl(refugeId) {
  return `${REFUGES_URL}/${encodeURIComponent(refugeId)}`;
}


/**
 * Builds the feedback endpoint for one refuge.
 */
export function refugeFeedbackUrl(refugeId) {
  return `${refugeDetailsUrl(refugeId)}/feedback`;
}


/**
 * Builds the feedback-summary endpoint for one refuge.
 */
export function refugeFeedbackSummaryUrl(refugeId) {
  return `${refugeFeedbackUrl(refugeId)}/summary`;
}


/**
 * Polling interval used by the congestion feature.
 * Minimum interval is 60 seconds.
 */
const configuredPollInterval = Number(
  process.env.NEXT_PUBLIC_CONGESTION_POLL_INTERVAL_MS
);

export const CONGESTION_POLL_INTERVAL_MS =
  Number.isFinite(configuredPollInterval)
    ? Math.max(60_000, configuredPollInterval)
    : 90_000;
