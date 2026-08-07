import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AlertsPage, { deduplicateAlerts } from "../components/AlertsPage.jsx";
import PointMapPanel from "../components/PointMapPanel.jsx";
import RefugesPage from "../components/RefugesPageApproved.jsx";
import {
  getPredictions,
  getPredictiveAlerts,
  getRefugeDetails,
  planRoute,
  searchRefuges,
} from "../services/api.js";


jest.mock("../services/api.js", () => ({
  getPredictions: jest.fn(),
  getPredictiveAlerts: jest.fn(),
  getRefugeDetails: jest.fn(),
  planRoute: jest.fn(),
  searchRefuges: jest.fn(),
}));


function refuge(overrides = {}) {
  return {
    refuge_id: 1,
    name: "Treasury Gardens",
    category: "Park",
    address: "2-18 Spring Street, Melbourne",
    latitude: -37.8144,
    longitude: 144.9754,
    distance_m: 240,
    estimated_travel_minutes: 3,
    opening_status: "open",
    opening_hours_summary: "Thu 00:00–23:59",
    sensory_suitability_description: "Potential quiet space; quietness is not guaranteed.",
    data_source: "City of Melbourne Open Data",
    data_last_updated: "2026-08-06T02:00:00Z",
    limitation_message: "Sensory refuge candidate. Quietness is not guaranteed.",
    ...overrides,
  };
}


function refugeResponse(results, message = null) {
  return { results, result_count: results.length, radius_m: 1000, selected_datetime: "2026-08-06T02:00:00Z", message };
}


function futureIso(minutes) {
  return new Date(Date.now() + minutes * 60_000).toISOString();
}


function prediction(overrides = {}) {
  return {
    prediction_id: 11,
    sensor_id: 4,
    location_name: "Bourke Street Mall",
    latitude: -37.8136,
    longitude: 144.9631,
    distance_m: 120,
    prediction_for: futureIso(45),
    predicted_count: 420,
    severity: "High",
    confidence: "Medium",
    generated_at: new Date().toISOString(),
    source_data_freshness: "recent",
    data_availability_status: "available",
    limitation_message: "Deterministic estimate.",
    data_source: "City of Melbourne Pedestrian Counting System",
    source_validated: true,
    route_relevant: false,
    ...overrides,
  };
}


function alert(overrides = {}) {
  return {
    alert_id: 5,
    deduplication_key: "4:forecast:predictive_crowd",
    prediction_id: 11,
    sensor_id: 4,
    location_name: "Bourke Street Mall",
    latitude: -37.8136,
    longitude: 144.9631,
    distance_m: 120,
    predicted_time: futureIso(45),
    severity: "High",
    confidence: "Medium",
    message: "Bourke Street Mall is predicted to reach High crowd severity.",
    suggested_action: "View the area on the map.",
    route_impact: "Nearby area; route impact not confirmed",
    status: "active",
    updated_at: new Date().toISOString(),
    data_freshness: "recent",
    source_validated: true,
    ...overrides,
  };
}


function mockGeolocation({ state = "prompt", position, error } = {}) {
  Object.defineProperty(globalThis.navigator, "permissions", {
    configurable: true,
    value: { query: jest.fn().mockResolvedValue({ state }) },
  });
  Object.defineProperty(globalThis.navigator, "geolocation", {
    configurable: true,
    value: {
      getCurrentPosition: jest.fn((success, failure) => {
        if (position) success({ coords: position });
        else if (error) failure({ PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3, ...error });
      }),
    },
  });
}


describe("Iteration 3 refuge discovery", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
    mockGeolocation();
    searchRefuges.mockResolvedValue(refugeResponse([refuge()]));
    getRefugeDetails.mockImplementation(async () => ({ ...refuge(), accessibility_notes: "Step-free access not confirmed." }));
    planRoute.mockResolvedValue({ routes: [{ is_recommended: true, estimated_travel_minutes: 4 }] });
  });

  it("renders the refuge page and asks for location only after a clear action", () => {
    render(<RefugesPage />);
    expect(screen.getByRole("heading", { name: "Find Refuges" })).toBeInTheDocument();
    expect(screen.getByText(/Location is used only to order/)).toBeInTheDocument();
    expect(globalThis.navigator.geolocation.getCurrentPosition).not.toHaveBeenCalled();
  });

  it("loads nearest-first refuges after location permission is granted", async () => {
    const user = userEvent.setup();
    mockGeolocation({ position: { latitude: -37.8136, longitude: 144.9631 } });
    searchRefuges.mockResolvedValueOnce(refugeResponse([
      refuge({ refuge_id: 1, name: "Near park", distance_m: 100 }),
      refuge({ refuge_id: 2, name: "Far library", category: "Library", distance_m: 500 }),
    ]));
    render(<RefugesPage />);
    await user.click(screen.getByRole("button", { name: "Use my current location" }));
    expect(await screen.findByRole("heading", { name: "Near park", level: 3 })).toBeInTheDocument();
    const cards = screen.getAllByRole("article");
    expect(within(cards[0]).getByText("100 m")).toBeInTheDocument();
    expect(within(cards[1]).getByText("500 m")).toBeInTheDocument();
  });

  it("reports denied permission without blocking manual location fallback", async () => {
    const user = userEvent.setup();
    mockGeolocation({ error: { code: 1 } });
    render(<RefugesPage />);
    await user.click(screen.getByRole("button", { name: "Use my current location" }));
    expect(await screen.findByText(/Location permission was denied/)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Search suburb or landmark" })).toBeEnabled();
  });

  it("supports controlled manual suburb search and map fallback", async () => {
    const user = userEvent.setup();
    render(<RefugesPage />);
    const input = screen.getByRole("combobox", { name: "Search suburb or landmark" });
    await user.clear(input);
    await user.type(input, "Carlton");
    await user.click(screen.getByRole("button", { name: "Use selected location" }));
    await waitFor(() => expect(searchRefuges).toHaveBeenCalledWith(expect.objectContaining({ latitude: -37.8001 }), expect.anything()));
    expect(screen.getByText(/Carlton selected manually/)).toBeInTheDocument();
  });

  it("updates category filters, radius, date-time, and all opening labels", async () => {
    const user = userEvent.setup();
    searchRefuges.mockResolvedValue(refugeResponse([
      refuge({ refuge_id: 1, name: "Open park", opening_status: "open" }),
      refuge({ refuge_id: 2, name: "Closed library", category: "Library", opening_status: "closed" }),
      refuge({ refuge_id: 3, name: "Unknown hours", category: "Library", opening_status: "hours_unavailable" }),
    ]));
    render(<RefugesPage />);
    await user.click(screen.getByRole("button", { name: "Use selected location" }));
    await screen.findByRole("heading", { name: "Open park", level: 3 });
    expect(screen.getAllByText("Open").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Closed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Opening hours unavailable").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("checkbox", { name: "Park" }));
    expect(screen.queryByRole("heading", { name: "Open park" })).not.toBeInTheDocument();
    await user.selectOptions(screen.getByRole("combobox", { name: "Search radius" }), "2000");
    await user.clear(screen.getByLabelText("Selected date and time"));
    fireEvent.change(screen.getByLabelText("Selected date and time"), { target: { value: "2026-08-07T10:30" } });
    await waitFor(() => expect(searchRefuges).toHaveBeenLastCalledWith(expect.objectContaining({ radius_m: 2000, selected_datetime: expect.stringContaining("2026-08-07") }), expect.anything()));
  });

  it("shows the radius recommendation when no refuges are found", async () => {
    const user = userEvent.setup();
    searchRefuges.mockResolvedValue(refugeResponse([], "No sensory refuge candidates were found within this radius. Try increasing the search radius."));
    render(<RefugesPage />);
    await user.click(screen.getByRole("button", { name: "Use selected location" }));
    expect(await screen.findByRole("heading", { name: "No nearby refuge locations were found" })).toBeInTheDocument();
    expect(screen.getByText(/increasing the search radius/)).toBeInTheDocument();
  });

  it("synchronises card, text-map and detail selection and reuses route planning for directions", async () => {
    const user = userEvent.setup();
    const library = refuge({ refuge_id: 2, name: "City Library", category: "Library", distance_m: 300 });
    searchRefuges.mockResolvedValue(refugeResponse([refuge(), library]));
    render(<RefugesPage />);
    await user.click(screen.getByRole("button", { name: "Use selected location" }));
    const mapButton = await screen.findByRole("button", { name: "City Library — Library" });
    await user.click(mapButton);
    expect(mapButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "City Library", level: 2 })).toBeInTheDocument();
    const libraryCard = screen.getByRole("heading", { name: "City Library", level: 3 }).closest("article");
    await user.click(within(libraryCard).getByRole("button", { name: "View details" }));
    await waitFor(() => expect(getRefugeDetails).toHaveBeenCalledWith(2, expect.anything()));
    await user.click(within(libraryCard).getByRole("button", { name: "Directions" }));
    await waitFor(() => expect(planRoute).toHaveBeenCalledWith(expect.objectContaining({ destination_latitude: library.latitude, travel_mode: "walking" })));
    expect(await screen.findByText(/Walking directions found/)).toBeInTheDocument();
  });
});


describe("Iteration 3 predictive alerts", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
    getPredictions.mockResolvedValue({ service_available: true, predictions: [prediction()], forecast_minutes: 60, message: null });
    getPredictiveAlerts.mockResolvedValue({ service_available: true, alerts: [alert()], preferences_temporary: true });
  });

  it("renders the timeline with predicted time, severity, confidence, freshness, and route impact", async () => {
    render(<AlertsPage />);
    expect(await screen.findByRole("heading", { name: "Bourke Street Mall" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Bourke Street Mall" }).closest("article").querySelector(".severity-badge")).toHaveTextContent("High");
    const card = screen.getByRole("heading", { name: "Bourke Street Mall" }).closest("article");
    expect(within(card).getByText(/Medium confidence/)).toBeInTheDocument();
    expect(within(card).getByText(/Nearby area; route impact not confirmed/)).toBeInTheDocument();
    expect(within(card).getByText(/recent source data/)).toBeInTheDocument();
  });

  it("shows the exact unavailable message and no fabricated prediction", async () => {
    getPredictions.mockRejectedValueOnce(new Error("Prediction services are temporarily unavailable."));
    getPredictiveAlerts.mockRejectedValueOnce(new Error("Prediction services are temporarily unavailable."));
    render(<AlertsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Prediction services are temporarily unavailable.");
    expect(screen.queryByRole("heading", { name: "Bourke Street Mall" })).not.toBeInTheDocument();
  });

  it("sends changed temporary preferences to backend filtering", async () => {
    const user = userEvent.setup();
    render(<AlertsPage />);
    await screen.findByRole("heading", { name: "Bourke Street Mall" });
    await user.selectOptions(screen.getByRole("combobox", { name: "Minimum severity" }), "moderate");
    await user.selectOptions(screen.getByRole("combobox", { name: "Maximum alert distance" }), "2000");
    await user.click(screen.getByRole("checkbox", { name: /Only when selected route/ }));
    await waitFor(() => expect(getPredictiveAlerts).toHaveBeenLastCalledWith(expect.objectContaining({
      minimum_severity: "moderate", maximum_distance_m: 2000, route_only: true,
    }), expect.anything()));
    expect(screen.getByText(/settings are temporary/)).toBeInTheDocument();
  });

  it("deduplicates updated alerts and keeps the newest version", () => {
    const old = alert({ message: "old", updated_at: "2026-08-06T01:00:00Z" });
    const latest = alert({ alert_id: 6, message: "latest", updated_at: "2026-08-06T02:00:00Z" });
    expect(deduplicateAlerts([old, latest])).toEqual([latest]);
  });

  it("synchronises View on map, links to alternatives, and dismisses without rerouting", async () => {
    const user = userEvent.setup();
    render(<AlertsPage />);
    await screen.findByRole("heading", { name: "Bourke Street Mall" });
    await user.click(screen.getByRole("button", { name: "View on map" }));
    expect(screen.getByRole("button", { name: "Bourke Street Mall — High, Medium confidence" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("link", { name: "Review alternative" })).toHaveAttribute("href", "/plan");
    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByRole("heading", { name: "Bourke Street Mall" })).not.toBeInTheDocument();
  });

  it("renders at a mobile viewport and keeps controls keyboard accessible", async () => {
    Object.defineProperty(globalThis, "innerWidth", { configurable: true, value: 390 });
    render(<AlertsPage />);
    expect(await screen.findByRole("combobox", { name: "Minimum severity" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Refresh predictions" })).toBeEnabled();
  });

  it("expanded map supports Escape-to-close and restores focus", async () => {
    const user = userEvent.setup();
    render(<PointMapPanel title="Test map" points={[]} selectedId={null} onSelect={() => {}} legend="Text legend" label="Test" />);
    const expand = screen.getByRole("button", { name: "Expand map" });
    await user.click(expand);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(expand).toHaveFocus();
  });
});
