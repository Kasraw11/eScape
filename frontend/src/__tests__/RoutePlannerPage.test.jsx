import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { planRoute } from "../services/api.js";
import GoogleMapPreview from "../components/GoogleMapPreview.jsx";
import RoutePlannerPage from "../components/RoutePlannerPage.jsx";

jest.mock("../services/api.js", () => ({
  planRoute: jest.fn(),
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

describe("RoutePlannerPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows validation when origin and destination match", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);

    await user.selectOptions(screen.getByLabelText(/destination/i), "bourke-street-mall");
    await user.click(screen.getByRole("button", { name: /generate route alternatives/i }));

    expect(await screen.findByText("Choose a destination different from the origin.")).toBeInTheDocument();
    expect(planRoute).not.toHaveBeenCalled();
  });

  it("shows validation when required fields are missing", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);

    await user.selectOptions(screen.getByLabelText(/origin/i), "");
    await user.click(screen.getByRole("button", { name: /generate route alternatives/i }));

    expect(await screen.findByText("Choose an origin.")).toBeInTheDocument();
    expect(planRoute).not.toHaveBeenCalled();
  });

  it("submits a valid journey and displays estimated travel time", async () => {
    const user = userEvent.setup();
    planRoute.mockResolvedValueOnce(response([route()]));

    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: /generate route alternatives/i }));

    await waitFor(() => expect(planRoute).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("12 min")).toBeInTheDocument();
    expect(screen.getAllByText("Walking").length).toBeGreaterThan(0);
    expect(screen.getByText("Low sensory load")).toHaveClass("sensory-indicator--low");
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("supports keyboard form submission", async () => {
    const user = userEvent.setup();
    planRoute.mockResolvedValueOnce(response([route()]));

    render(<RoutePlannerPage />);
    screen.getByRole("button", { name: /generate route alternatives/i }).focus();
    await user.keyboard("{Enter}");

    await waitFor(() => expect(planRoute).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("12 min")).toBeInTheDocument();
  });

  it("marks the recommended route returned by the backend", async () => {
    const user = userEvent.setup();
    planRoute.mockResolvedValueOnce(response([route({ route_identifier: "calmest-route" })]));

    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: /generate route alternatives/i }));

    expect(await screen.findByText("Recommended lowest sensory route")).toBeInTheDocument();
    expect(screen.getByText(/Recommended route:/)).toHaveTextContent("calmest-route");
  });

  it("renders multiple route alternatives for comparison", async () => {
    const user = userEvent.setup();
    planRoute.mockResolvedValueOnce(
      response([
        route({ route_identifier: "calmest-route" }),
        route({
          route_identifier: "faster-route",
          estimated_travel_minutes: 9,
          sensory_score: 2.62,
          sensory_indicator: "high",
          is_recommended: false,
        }),
      ]),
    );

    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: /generate route alternatives/i }));

    expect((await screen.findAllByText(/calmest-route/)).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("faster-route")).toBeInTheDocument();
    expect(screen.getByText("9 min")).toBeInTheDocument();
    expect(screen.getByText("High sensory load")).toHaveClass("sensory-indicator--high");
  });

  it("warns when pedestrian data is unavailable", async () => {
    const user = userEvent.setup();
    planRoute.mockResolvedValueOnce(
      response([
        route({
          route_identifier: "unconfirmed-route",
          sensory_score: null,
          sensory_indicator: "unavailable",
          pedestrian_data_availability: "unavailable",
          matched_sensor_count: 0,
          sensor_coverage_ratio: 0,
          warning_message: "Congestion and sensory information cannot be fully confirmed for this route.",
        }),
      ]),
    );

    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: /generate route alternatives/i }));

    expect(await screen.findByText("Pedestrian data unavailable")).toBeInTheDocument();
    expect(screen.getByText("Congestion and sensory information cannot be fully confirmed for this route.")).toBeInTheDocument();
    expect(screen.getByText("Sensory data unavailable")).toBeInTheDocument();
    expect(screen.getByText("Unconfirmed")).toBeInTheDocument();
    expect(screen.queryByText("Low sensory load")).not.toBeInTheDocument();
    expect(screen.queryByText("High sensory load")).not.toBeInTheDocument();
  });

  it("shows no sensory recommendation when all routes are unavailable", async () => {
    const user = userEvent.setup();
    planRoute.mockResolvedValueOnce(
      response([
        route({
          route_identifier: "unavailable-a",
          sensory_score: null,
          sensory_indicator: "unavailable",
          is_recommended: false,
          pedestrian_data_availability: "unavailable",
          matched_sensor_count: 0,
          sensor_coverage_ratio: 0,
          warning_message: "Sensory information unavailable.",
        }),
        route({
          route_identifier: "unavailable-b",
          sensory_score: null,
          sensory_indicator: "unavailable",
          is_recommended: false,
          pedestrian_data_availability: "unavailable",
          matched_sensor_count: 0,
          sensor_coverage_ratio: 0,
          warning_message: "Sensory information unavailable.",
        }),
      ]),
    );

    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: /generate route alternatives/i }));

    expect(await screen.findByText(/Sensory-aware recommendation cannot be confirmed/i)).toBeInTheDocument();
    expect(screen.queryByText(/Recommended route:/)).not.toBeInTheDocument();
  });

  it("shows backend errors without clearing the page", async () => {
    const user = userEvent.setup();
    planRoute.mockRejectedValueOnce(new Error("Route provider is unavailable"));

    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: /generate route alternatives/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Route provider is unavailable");
    expect(screen.getByText("Plan a journey")).toBeInTheDocument();
  });

  it("shows a loading state while the route request is pending", async () => {
    const user = userEvent.setup();
    let resolveRequest;
    planRoute.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );

    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: /generate route alternatives/i }));

    expect(screen.getByRole("status")).toHaveTextContent("Finding route alternatives and checking pedestrian data...");

    resolveRequest(response([route()]));
    expect((await screen.findAllByText(/route-low/)).length).toBeGreaterThanOrEqual(2);
  });

  it("shows the map missing-key fallback", () => {
    const previousKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
    process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY = "";

    render(<GoogleMapPreview />);

    expect(screen.getByText("Map preview is unavailable until `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY` is configured.")).toBeInTheDocument();
    if (previousKey === undefined) {
      delete process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
    } else {
      process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY = previousKey;
    }
  });

  it("draws returned route polylines when the map key is configured", async () => {
    const previousKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
    const previousGoogle = window.google;
    process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY = "test-browser-key";

    const map = { fitBounds: jest.fn() };
    const bounds = { extend: jest.fn() };
    const polyline = { addListener: jest.fn() };
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
        routes={[
          route({
            encoded_polyline: "_p~iF~ps|U_ulLnnqC_mqNvxq`@",
            route_identifier: "route-low",
          }),
        ]}
        selectedRouteIdentifier="route-low"
      />,
    );

    await waitFor(() => expect(window.google.maps.Polyline).toHaveBeenCalledTimes(1));
    expect(bounds.extend).toHaveBeenCalled();
    expect(map.fitBounds).toHaveBeenCalledWith(bounds);
    expect(screen.getByRole("button", { name: /route-low - recommended/i })).toBeInTheDocument();

    if (previousKey === undefined) {
      delete process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
    } else {
      process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY = previousKey;
    }
    window.google = previousGoogle;
  });

  it("renders at a mobile-compatible width without crashing", () => {
    window.innerWidth = 390;
    window.dispatchEvent(new window.Event("resize"));

    render(<RoutePlannerPage />);

    expect(screen.getByText("Plan a journey")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generate route alternatives/i })).toBeInTheDocument();
  });
});
