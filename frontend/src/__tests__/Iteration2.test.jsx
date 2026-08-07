import { afterEach } from "@jest/globals";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import GoogleMapPreview from "../components/GoogleMapPreview.jsx";
import RoutePlannerPage from "../components/RoutePlannerPage.jsx";
import useCongestionPolling from "../hooks/useCongestionPolling.js";
import { getRouteCongestion, planRoute } from "../services/api.js";


jest.mock("../services/api.js", () => ({
  getRouteCongestion: jest.fn(),
  planRoute: jest.fn(),
  submitJourneyFeedback: jest.fn(),
}));


const encodedPolyline = "_p~iF~ps|U_ulLnnqC_mqNvxq`@";
const updatedAt = "2026-08-06T02:15:00Z";

function segment(overrides = {}) {
  return {
    route_segment_id: 101,
    segment_sequence: 1,
    encoded_polyline: encodedPolyline,
    distance_m: 420,
    duration_seconds: 600,
    matched_sensor_count: 1,
    congestion_level: "low",
    sensory_score: 0.5,
    data_availability: "available",
    pedestrian_count: 80,
    threshold_exceeded: false,
    data_source: "realtime",
    observed_at: updatedAt,
    freshness_status: "live",
    ...overrides,
  };
}

function route(overrides = {}) {
  return {
    route_id: 11,
    route_identifier: "calm-route",
    encoded_polyline: encodedPolyline,
    estimated_travel_minutes: 12,
    travel_mode: "walking",
    sensory_score: 0.5,
    sensory_indicator: "Low",
    is_recommended: true,
    pedestrian_data_availability: "available",
    data_availability_status: "available",
    matched_sensor_count: 1,
    sensor_coverage_ratio: 1,
    route_segments: [segment()],
    warning_message: null,
    threshold_exceeded: false,
    qualifies_preference: true,
    recommendation_explanation: "Meets crowd preference level 3 with a lower pedestrian-density score.",
    data_freshness: "live",
    observed_at: updatedAt,
    updated_at: updatedAt,
    ...overrides,
  };
}

function planResponse(routes, overrides = {}) {
  return {
    recommended_route_identifier: routes.find((item) => item.is_recommended)?.route_identifier || null,
    routes,
    preferred_crowd_threshold: 3,
    threshold_message: "One or more routes meet the selected crowd preference.",
    all_routes_high: false,
    personalised_recommendations_available: true,
    ...overrides,
  };
}

function congestionResponse(overrides = {}) {
  return {
    route_id: 11,
    route_identifier: "calm-route",
    congestion_status: "Low",
    sensory_score: 0.5,
    sensory_indicator: "Low",
    threshold_exceeded: false,
    preferred_crowd_threshold: 3,
    updated_at: updatedAt,
    data_freshness: "live",
    route_segments: [segment()],
    alternatives: [],
    meaningful_change: false,
    notification: null,
    warning_messages: [],
    ...overrides,
  };
}

async function submit(user, routes, overrides) {
  planRoute.mockResolvedValueOnce(planResponse(routes, overrides));
  await user.click(screen.getByRole("button", { name: "Find routes" }));
  await waitFor(() => expect(planRoute).toHaveBeenCalled());
  await user.click(await screen.findByRole("button", { name: new RegExp(`Select route 1, ${routes[0].route_identifier}`, "i") }));
}

function HookHarness({ routeId = 11, intervalMs = 1_000 }) {
  const state = useCongestionPolling(routeId, { intervalMs });
  return (
    <div>
      <span data-testid="score">{state.congestion?.sensory_score ?? "none"}</span>
      <span data-testid="refresh-error">{state.refreshError}</span>
    </div>
  );
}


describe("Iteration 2 route experience", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
    delete window.google;
    getRouteCongestion.mockResolvedValue(congestionResponse());
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders the route preference control backed by the five crowd thresholds", () => {
    render(<RoutePlannerPage />);
    const preference = screen.getByRole("combobox", { name: "Route preference" });
    expect(preference).toHaveValue("3");
    expect(screen.getByRole("option", { name: /Quietest available/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Most direct options/ })).toBeInTheDocument();
  });

  it("sends the selected threshold in the route-planning request", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    await user.selectOptions(screen.getByRole("combobox", { name: "Route preference" }), "1");
    await submit(user, [route()]);
    expect(planRoute).toHaveBeenCalledWith(expect.objectContaining({ preferred_crowd_threshold: 1 }));
  });

  it("renders congestion freshness, recommendation reasoning, and last-updated time", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    await submit(user, [route()]);
    await user.click(screen.getByText("View details"));
    expect(screen.getByText("live")).toBeInTheDocument();
    expect(screen.getByText(/Meets crowd preference level 3/)).toBeInTheDocument();
    expect(screen.getByText(/Last updated/)).toBeInTheDocument();
  });

  it("starts congestion polling when a persisted route is selected", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    await submit(user, [route()]);
    await user.click(screen.getByRole("button", { name: "Start journey" }));
    await waitFor(() => expect(getRouteCongestion).toHaveBeenCalledWith(11, expect.objectContaining({ signal: expect.anything() })));
    expect(screen.getByText(/Trip started/)).toBeInTheDocument();
  });

  it("aborts congestion polling when the results component unmounts", async () => {
    let capturedSignal;
    getRouteCongestion.mockImplementation((routeId, options) => {
      capturedSignal = options.signal;
      return new Promise(() => {});
    });
    const view = render(<HookHarness />);
    await waitFor(() => expect(capturedSignal).toBeDefined());
    view.unmount();
    expect(capturedSignal.aborted).toBe(true);
  });

  it("does not overlap polling requests", async () => {
    jest.useFakeTimers();
    getRouteCongestion.mockReturnValue(new Promise(() => {}));
    render(<HookHarness />);
    await Promise.resolve();
    expect(getRouteCongestion).toHaveBeenCalledTimes(1);
    act(() => jest.advanceTimersByTime(5_000));
    expect(getRouteCongestion).toHaveBeenCalledTimes(1);
  });

  it("retains the last valid congestion state after a temporary refresh failure", async () => {
    jest.useFakeTimers();
    getRouteCongestion
      .mockResolvedValueOnce(congestionResponse({ sensory_score: 0.6 }))
      .mockRejectedValueOnce(new Error("Temporary refresh failure"));
    render(<HookHarness />);
    await waitFor(() => expect(screen.getByTestId("score")).toHaveTextContent("0.6"));
    act(() => jest.advanceTimersByTime(1_000));
    await waitFor(() => expect(screen.getByTestId("refresh-error")).toHaveTextContent("Temporary refresh failure"));
    expect(screen.getByTestId("score")).toHaveTextContent("0.6");
  });

  it("shows a meaningful congestion notification once and supports dismissal", async () => {
    const user = userEvent.setup();
    getRouteCongestion.mockResolvedValue(congestionResponse({
      threshold_exceeded: true,
      meaningful_change: true,
      notification: {
        change_key: "11:101:high:1:2026-08-06T02:15:00Z",
        route_id: 11,
        route_segment_id: 101,
        segment_sequence: 1,
        congestion_level: "high",
        threshold_exceeded: true,
        updated_at: updatedAt,
        message: "Segment 1 is now high congestion. Your crowd preference is exceeded.",
      },
      route_segments: [segment({ congestion_level: "high", threshold_exceeded: true })],
    }));
    render(<RoutePlannerPage />);
    await submit(user, [route()]);
    await user.click(screen.getByRole("button", { name: "Start journey" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Segment 1 is now high congestion");
    await user.click(screen.getByRole("button", { name: "Dismiss update" }));
    expect(screen.queryByText("Route segment 1 changed")).not.toBeInTheDocument();
  });

  it("offers a lower-congestion alternative without switching automatically", async () => {
    const user = userEvent.setup();
    const high = route({ route_id: 21, route_identifier: "busy-route", is_recommended: true, sensory_indicator: "High", sensory_score: 1.8, threshold_exceeded: true, qualifies_preference: false });
    const calm = route({ route_id: 22, route_identifier: "calm-alternative", is_recommended: false });
    getRouteCongestion.mockResolvedValue(congestionResponse({
      route_id: 21,
      route_identifier: "busy-route",
      threshold_exceeded: true,
      alternatives: [{
        route_id: 22,
        route_identifier: "calm-alternative",
        sensory_score: 0.5,
        sensory_indicator: "Low",
        estimated_travel_minutes: 12,
        threshold_exceeded: false,
        recommendation_explanation: "Meets crowd preference level 3 with a lower pedestrian-density score.",
      }],
    }));
    render(<RoutePlannerPage />);
    await submit(user, [high, calm]);
    expect(await screen.findByRole("heading", { name: "Lower-congestion alternatives" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select route 1, busy-route/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Select route 2, calm-alternative/ })).toHaveAttribute("aria-pressed", "false");
  });

  it("keeps the current route when requested", async () => {
    const user = userEvent.setup();
    const high = route({ route_id: null, route_identifier: "busy-route", threshold_exceeded: true, qualifies_preference: false });
    const calm = route({ route_id: 12, route_identifier: "calm-alternative", is_recommended: false });
    render(<RoutePlannerPage />);
    await submit(user, [high, calm]);
    await user.click(screen.getByRole("button", { name: "Keep current route" }));
    expect(screen.queryByRole("heading", { name: "Lower-congestion alternatives" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select route 1, busy-route/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("selects an offered alternative only after explicit confirmation and synchronises cards", async () => {
    const user = userEvent.setup();
    const high = route({ route_id: null, route_identifier: "busy-route", threshold_exceeded: true, qualifies_preference: false });
    const calm = route({ route_id: 12, route_identifier: "calm-alternative", is_recommended: false });
    render(<RoutePlannerPage />);
    await submit(user, [high, calm]);
    await user.click(screen.getByRole("button", { name: "Select alternative route" }));
    expect(screen.getByRole("button", { name: /Select route 2, calm-alternative/ })).toHaveAttribute("aria-pressed", "true");
    expect(planRoute).toHaveBeenCalledTimes(1);
  });

  it("shows the no-qualifying-alternative message", async () => {
    const user = userEvent.setup();
    const high = route({ route_id: null, threshold_exceeded: true, qualifies_preference: false });
    render(<RoutePlannerPage />);
    await submit(user, [high], { threshold_message: "No route meets the selected crowd preference; the lowest-impact route is recommended." });
    expect(await screen.findByText(/No route meets the selected crowd preference/)).toBeInTheDocument();
  });

  it("shows the all-routes-high warning", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    await submit(user, [route({ sensory_indicator: "High", threshold_exceeded: true, qualifies_preference: false })], { all_routes_high: true });
    expect(await screen.findByText(/All available routes contain high-congestion segments/)).toBeInTheDocument();
  });

  it("renders segment-level congestion colours and an explicit map legend", async () => {
    process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY = "test-browser-key";
    const polylineInstances = [];
    window.google = {
      maps: {
        Map: jest.fn(() => ({ fitBounds: jest.fn() })),
        Marker: jest.fn(),
        LatLngBounds: jest.fn(() => ({ extend: jest.fn() })),
        Polyline: jest.fn((options) => {
          const instance = { options, addListener: jest.fn(), setMap: jest.fn() };
          polylineInstances.push(instance);
          return instance;
        }),
      },
    };
    render(<GoogleMapPreview routes={[route({ route_segments: [
      segment({ route_segment_id: 1, segment_sequence: 1, congestion_level: "low" }),
      segment({ route_segment_id: 2, segment_sequence: 2, congestion_level: "high" }),
      segment({ route_segment_id: 3, segment_sequence: 3, congestion_level: null, data_availability: "unavailable" }),
    ] })]} selectedRouteIdentifier="calm-route" />);
    await waitFor(() => expect(window.google.maps.Polyline).toHaveBeenCalledTimes(3));
    expect(polylineInstances.map((item) => item.options.strokeColor)).toEqual(["#2F9478", "#DC4949", "#64748b"]);
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });
});
