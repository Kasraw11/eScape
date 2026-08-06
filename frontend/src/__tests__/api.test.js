import { API_BASE_URL, normalizeApiBaseUrl, routeCongestionUrl, ROUTE_PLANNING_URL } from "../config/api.js";
import {
  getPredictions,
  getPredictiveAlerts,
  getRefugeDetails,
  getRouteCongestion,
  planRoute,
  searchRefuges,
} from "../services/api.js";

const requestPayload = {
  origin_latitude: -37.81362,
  origin_longitude: 144.96307,
  destination_latitude: -37.81827,
  destination_longitude: 144.96706,
  travel_mode: "walking",
};

function mockResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: jest.fn().mockResolvedValue(payload),
  };
}

describe("route-planning API client", () => {
  beforeEach(() => {
    globalThis.fetch = jest.fn();
  });

  it("normalizes configured API URLs and constructs the exact route endpoint", () => {
    expect(normalizeApiBaseUrl("  http://127.0.0.1:8000///  ")).toBe("http://127.0.0.1:8000");
    expect(normalizeApiBaseUrl("")).toBe("http://127.0.0.1:8000");
    expect(API_BASE_URL).toBe("http://127.0.0.1:8000");
    expect(ROUTE_PLANNING_URL).toBe("http://127.0.0.1:8000/api/routes/plan");
    expect(routeCongestionUrl(42)).toBe("http://127.0.0.1:8000/api/routes/42/congestion");
  });

  it("posts the correct JSON body and returns a successful response", async () => {
    const payload = { recommended_route_identifier: null, routes: [] };
    globalThis.fetch.mockResolvedValueOnce(mockResponse(200, payload));

    await expect(planRoute(requestPayload)).resolves.toEqual(payload);
    expect(globalThis.fetch).toHaveBeenCalledWith("http://127.0.0.1:8000/api/routes/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestPayload),
    });
  });

  it("surfaces FastAPI 422 validation details", async () => {
    globalThis.fetch.mockResolvedValueOnce(mockResponse(422, {
      detail: [{ msg: "Input should be 'walking' or 'transit'" }],
    }));

    await expect(planRoute(requestPayload)).rejects.toThrow("Input should be 'walking' or 'transit'");
  });

  it("distinguishes an HTTP 500 response from a network failure", async () => {
    globalThis.fetch.mockResolvedValueOnce(mockResponse(500, null));

    await expect(planRoute(requestPayload)).rejects.toThrow("The local backend encountered an error while planning the route.");
  });

  it("explains genuine local-backend network failures", async () => {
    globalThis.fetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(planRoute(requestPayload)).rejects.toThrow(
      "Unable to connect to the local backend. Confirm FastAPI is running on http://127.0.0.1:8000.",
    );
  });

  it("requests current congestion for only the selected persisted route", async () => {
    const payload = { route_id: 42, data_freshness: "live", route_segments: [] };
    const controller = new globalThis.AbortController();
    globalThis.fetch.mockResolvedValueOnce(mockResponse(200, payload));
    await expect(getRouteCongestion(42, { signal: controller.signal })).resolves.toEqual(payload);
    expect(globalThis.fetch).toHaveBeenCalledWith("http://127.0.0.1:8000/api/routes/42/congestion", {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
  });

  it("surfaces a safe temporary congestion refresh failure", async () => {
    globalThis.fetch.mockResolvedValueOnce(mockResponse(503, { detail: "Current congestion data is temporarily unavailable" }));
    await expect(getRouteCongestion(42)).rejects.toThrow("Current congestion data is temporarily unavailable");
  });

  it("constructs validated refuge search and detail query strings", async () => {
    globalThis.fetch
      .mockResolvedValueOnce(mockResponse(200, { results: [] }))
      .mockResolvedValueOnce(mockResponse(200, { refuge_id: 7 }));
    await searchRefuges({ latitude: -37.8, longitude: 144.9, radius_m: 2000, category: "library" });
    await getRefugeDetails(7, { latitude: -37.8, longitude: 144.9 });
    expect(globalThis.fetch.mock.calls[0][0]).toContain("/api/refuges?latitude=-37.8&longitude=144.9&radius_m=2000&category=library");
    expect(globalThis.fetch.mock.calls[1][0]).toContain("/api/refuges/7?latitude=-37.8&longitude=144.9");
  });

  it("requests predictions and backend-filtered temporary alert preferences", async () => {
    globalThis.fetch
      .mockResolvedValueOnce(mockResponse(200, { predictions: [] }))
      .mockResolvedValueOnce(mockResponse(200, { alerts: [] }));
    await getPredictions({ latitude: -37.8, longitude: 144.9, forecast_minutes: 60, minimum_severity: "low" });
    await getPredictiveAlerts({ latitude: -37.8, longitude: 144.9, enabled: true, minimum_severity: "high", route_only: false });
    expect(globalThis.fetch.mock.calls[0][0]).toContain("/api/predictions?");
    expect(globalThis.fetch.mock.calls[0][0]).toContain("forecast_minutes=60");
    expect(globalThis.fetch.mock.calls[1][0]).toContain("/api/alerts/predictive?");
    expect(globalThis.fetch.mock.calls[1][0]).toContain("minimum_severity=high");
  });

  it("preserves the exact predictive-service unavailable message", async () => {
    globalThis.fetch.mockResolvedValueOnce(mockResponse(503, { detail: "Prediction services are temporarily unavailable." }));
    await expect(getPredictions({ latitude: -37.8, longitude: 144.9 })).rejects.toThrow(
      "Prediction services are temporarily unavailable.",
    );
  });
});
