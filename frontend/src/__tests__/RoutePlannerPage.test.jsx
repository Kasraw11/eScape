import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import GoogleMapPreview from "../components/GoogleMapPreview.jsx";
import RoutePlannerPage from "../components/RoutePlannerPage.jsx";
import { getRouteCongestion, planRoute } from "../services/api.js";

jest.mock("../services/api.js", () => ({
  getRouteCongestion: jest.fn(),
  planRoute: jest.fn(),
  submitJourneyFeedback: jest.fn(),
}));

const baseSegment = {
  segment_sequence: 1,
  encoded_polyline: "sample",
  distance_m: 420,
  duration_seconds: 600,
  matched_sensor_count: 2,
  congestion_level: "low",
  sensory_score: 0.24,
  data_availability: "available",
};

function route(overrides = {}) {
  return {
    route_identifier: "route-low",
    encoded_polyline: "sample",
    estimated_travel_minutes: 12,
    travel_mode: "walking",
    sensory_score: 0.24,
    sensory_indicator: "low",
    is_recommended: true,
    pedestrian_data_availability: "available",
    data_availability_status: "available",
    matched_sensor_count: 2,
    sensor_coverage_ratio: 1,
    route_segments: [baseSegment],
    warning_message: null,
    ...overrides,
  };
}

function response(routes) {
  const recommended = routes.find((candidate) => candidate.is_recommended);
  return {
    recommended_route_identifier: recommended?.route_identifier || null,
    routes,
  };
}

async function submitRoutes(user, routes) {
  planRoute.mockResolvedValueOnce(response(routes));
  await user.click(screen.getByRole("button", { name: "Find routes" }));
  await waitFor(() => expect(planRoute).toHaveBeenCalledTimes(1));
}

describe("RoutePlannerPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getRouteCongestion.mockResolvedValue({});
    delete process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
    delete window.google;
  });

  it("renders the journey form and segmented travel-mode controls", () => {
    render(<RoutePlannerPage />);

    expect(screen.getByRole("heading", { name: "Plan your journey" })).toBeInTheDocument();
    expect(screen.getByLabelText("Origin")).toBeInTheDocument();
    expect(screen.getByLabelText("Destination")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Walking" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Public transport" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Find routes" })).toBeInTheDocument();
  });

  it("shows inline validation and does not submit invalid journeys", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);

    await user.clear(screen.getByLabelText("Destination"));
    await user.type(screen.getByLabelText("Destination"), "Bourke");
    await user.click(screen.getByRole("option", { name: "Bourke Street Mall" }));
    await user.click(screen.getByRole("button", { name: "Find routes" }));

    expect((await screen.findAllByText("Origin and destination cannot be the same.")).length).toBe(2);
    expect(screen.getByRole("combobox", { name: /Destination/ })).toHaveAttribute("aria-invalid", "true");
    expect(planRoute).not.toHaveBeenCalled();
  });

  it("submits the existing API payload and renders route cards", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: "Public transport" }));
    await submitRoutes(user, [route({ travel_mode: "transit" })]);

    expect(planRoute).toHaveBeenCalledWith({
      origin_latitude: -37.81362,
      origin_longitude: 144.96307,
      destination_latitude: -37.81827,
      destination_longitude: 144.96706,
      travel_mode: "transit",
      preferred_crowd_threshold: 3,
    });
    expect(await screen.findByRole("button", { name: /Select route 1, route-low/i })).toBeInTheDocument();
    expect(screen.getByText("12 min")).toBeInTheDocument();
    expect(screen.getAllByText("Public transport").length).toBeGreaterThan(1);
    await user.click(screen.getByText("View details"));
    expect(screen.getByText("100% crowd-data coverage")).toBeInTheDocument();
    expect(screen.getByText("Matched sensors").closest("div")).toHaveTextContent("2");
  });

  it("shows recommended badges plus low, high, and unavailable text labels", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    await submitRoutes(user, [
      route(),
      route({ route_identifier: "route-high", sensory_indicator: "high", sensory_score: 2.4, is_recommended: false }),
      route({
        route_identifier: "route-unknown",
        sensory_indicator: "unavailable",
        sensory_score: null,
        is_recommended: false,
        pedestrian_data_availability: "unavailable",
        matched_sensor_count: 0,
        sensor_coverage_ratio: 0,
      }),
    ]);

    expect(await screen.findByText("Recommended")).toBeInTheDocument();
    expect(screen.getByLabelText("Low sensory impact")).toBeInTheDocument();
    expect(screen.getByLabelText("High sensory impact")).toBeInTheDocument();
    expect(screen.getByLabelText("Sensory information unavailable")).toBeInTheDocument();
  });

  it("keeps data-coverage information and missing-data warnings visible", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    await submitRoutes(user, [route({
      route_identifier: "unconfirmed-route",
      sensory_indicator: "unavailable",
      sensory_score: null,
      is_recommended: false,
      pedestrian_data_availability: "unavailable",
      matched_sensor_count: 0,
      sensor_coverage_ratio: 0,
      warning_message: "Congestion and sensory information cannot be fully confirmed for this route.",
    })]);

    expect(await screen.findByRole("heading", { name: "Pedestrian-data coverage" })).toBeInTheDocument();
    expect(screen.getByText(/Congestion and sensory information cannot be fully confirmed/)).toBeInTheDocument();
    expect(screen.getByText(/Sensory-aware recommendation cannot be confirmed/)).toBeInTheDocument();
  });

  it("renders the compact map preview and missing-key fallback", () => {
    render(<GoogleMapPreview />);

    expect(screen.getByRole("heading", { name: "Map and details" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Expand route map" })).toBeInTheDocument();
    expect(screen.getByText(/NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY/)).toBeInTheDocument();
  });

  it("opens the expanded map from its expand button and closes it", async () => {
    const user = userEvent.setup();
    render(<GoogleMapPreview routes={[route()]} selectedRouteIdentifier="route-low" />);

    await user.click(screen.getByRole("button", { name: "Expand route map" }));
    expect(screen.getByRole("dialog", { name: "Route preview" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close expanded map" })).toHaveFocus();

    await user.click(screen.getByRole("button", { name: "Close expanded map" }));
    expect(screen.queryByRole("dialog", { name: "Route preview" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Expand route map" })).toHaveFocus();
  });

  it("opens from the map preview and closes with Escape", async () => {
    const user = userEvent.setup();
    render(<GoogleMapPreview routes={[route()]} selectedRouteIdentifier="route-low" />);

    await user.click(screen.getByLabelText("Open expanded route map"));
    expect(screen.getByRole("dialog", { name: "Route preview" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Route preview" })).not.toBeInTheDocument();
  });

  it("traps keyboard focus inside the expanded map", async () => {
    const user = userEvent.setup();
    render(<GoogleMapPreview />);

    await user.click(screen.getByRole("button", { name: "Expand route map" }));
    const closeButton = screen.getByRole("button", { name: "Close expanded map" });
    expect(closeButton).toHaveFocus();
    await user.tab();
    expect(closeButton).toHaveFocus();
    await user.tab({ shift: true });
    expect(closeButton).toHaveFocus();
  });

  it("keeps route-card and compact-map selection synchronised", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    await submitRoutes(user, [
      route({ route_identifier: "calmest-route" }),
      route({ route_identifier: "faster-route", sensory_indicator: "high", is_recommended: false }),
    ]);

    const fasterCard = await screen.findByRole("button", { name: "Select route 2, faster-route" });
    await user.click(fasterCard);

    expect(fasterCard).toHaveAttribute("aria-pressed", "true");
    const compactSelector = screen.getByRole("button", { name: "Route 2" });
    expect(compactSelector).toHaveClass("map-route-selector__button--active");
    expect(screen.getAllByText("faster-route selected").length).toBeGreaterThanOrEqual(1);
    expect(planRoute).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Route 1 · Recommended" }));
    expect(fasterCard).toHaveAttribute("aria-pressed", "false");
    expect(planRoute).toHaveBeenCalledTimes(1);
  });

  it("supports keyboard route-card selection", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    await submitRoutes(user, [route(), route({ route_identifier: "route-high", is_recommended: false })]);

    const secondCard = await screen.findByRole("button", { name: "Select route 2, route-high" });
    secondCard.focus();
    await user.keyboard("{Enter}");
    expect(secondCard).toHaveAttribute("aria-pressed", "true");
  });

  it("shows loading and API error states in live regions", async () => {
    const user = userEvent.setup();
    let rejectRequest;
    planRoute.mockReturnValueOnce(new Promise((resolve, reject) => { rejectRequest = reject; }));
    render(<RoutePlannerPage />);

    await user.click(screen.getByRole("button", { name: "Find routes" }));
    expect(screen.getByRole("status")).toHaveTextContent("Finding routes");
    expect(screen.getByRole("button", { name: "Finding routes…" })).toBeDisabled();

    rejectRequest(new Error("Route provider is unavailable"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Route provider is unavailable");
    expect(screen.getByRole("heading", { name: "Plan your journey" })).toBeInTheDocument();
  });

  it("draws returned route polylines when the map key is configured", async () => {
    process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY = "test-browser-key";
    const onSelectRoute = jest.fn();
    const map = { fitBounds: jest.fn() };
    const bounds = { extend: jest.fn() };
    const polyline = { addListener: jest.fn(), setMap: jest.fn() };
    window.google = {
      maps: {
        Map: jest.fn(() => map),
        Marker: jest.fn(),
        LatLngBounds: jest.fn(() => bounds),
        Polyline: jest.fn(() => polyline),
      },
    };

    render(
      <GoogleMapPreview
        routes={[route({ encoded_polyline: "_p~iF~ps|U_ulLnnqC_mqNvxq`@" })]}
        selectedRouteIdentifier="route-low"
        onSelectRoute={onSelectRoute}
      />,
    );

    await waitFor(() => expect(window.google.maps.Polyline).toHaveBeenCalledTimes(1));
    expect(bounds.extend).toHaveBeenCalled();
    expect(map.fitBounds).toHaveBeenCalledWith(bounds, 32);
    expect(screen.getByRole("button", { name: "Route 1 · Recommended" })).toBeInTheDocument();

    const polylineClickHandler = polyline.addListener.mock.calls.find(([eventName]) => eventName === "click")[1];
    polylineClickHandler();
    expect(onSelectRoute).toHaveBeenCalledWith("route-low");
    expect(planRoute).not.toHaveBeenCalled();
  });

  it("renders at mobile widths without crashing or losing controls", () => {
    window.innerWidth = 375;
    window.dispatchEvent(new window.Event("resize"));
    render(<RoutePlannerPage />);

    expect(screen.getByRole("heading", { name: "Plan your journey" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Find routes" })).toBeInTheDocument();
    expect(screen.getByLabelText("Open expanded route map")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Current trip" })).toBeInTheDocument();
  });
});
