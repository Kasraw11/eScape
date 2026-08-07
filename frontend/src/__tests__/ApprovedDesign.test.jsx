import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AppShell from "../components/app/AppShell.jsx";
import HomePage from "../components/HomePage.jsx";
import JourneyForm from "../components/JourneyForm.jsx";
import RoutePlannerPage from "../components/RoutePlannerPage.jsx";
import SettingsPage from "../components/SettingsPage.jsx";
import { getRouteCongestion, planRoute, submitJourneyFeedback } from "../services/api.js";

jest.mock("next/navigation", () => ({ usePathname: () => "/plan" }));
jest.mock("../services/api.js", () => ({ getRouteCongestion: jest.fn(), planRoute: jest.fn(), submitJourneyFeedback: jest.fn() }));

const plannedRoute = {
  route_id: 14,
  route_identifier: "calm-route",
  estimated_travel_minutes: 12,
  travel_mode: "walking",
  sensory_score: 0.3,
  sensory_indicator: "Low",
  is_recommended: true,
  qualifies_preference: true,
  threshold_exceeded: false,
  pedestrian_data_availability: "available",
  matched_sensor_count: 2,
  sensor_coverage_ratio: 1,
  data_freshness: "live",
  route_segments: [{ segment_sequence: 1, distance_m: 500, congestion_level: "low", data_availability: "available" }],
};

describe("approved application structure", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
    getRouteCongestion.mockResolvedValue({});
    submitJourneyFeedback.mockResolvedValue({ feedback_id: 1 });
  });

  it("shows the approved five desktop and mobile primary entries with no Live Journey entry", () => {
    render(<AppShell><p>Page</p></AppShell>);
    const desktop = screen.getByRole("navigation", { name: "Primary navigation" });
    const mobile = screen.getByRole("navigation", { name: "Mobile primary navigation" });
    expect(within(desktop).getAllByRole("link").map((link) => link.textContent)).toEqual(["Home", "Plan", "Find Refuges", "Alerts", "Settings"]);
    expect(within(mobile).getAllByRole("link").map((link) => link.textContent)).toEqual(["Home", "Plan", "Refuges", "Alerts", "Settings"]);
    expect(screen.queryByText(/Live Journey/i)).not.toBeInTheDocument();
    expect(within(desktop).getByRole("link", { name: "Plan" })).toHaveAttribute("aria-current", "page");
  });

  it("keeps Home introductory and leaves journey planning on Plan", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: "You deserve a calmer journey." })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(4);
    expect(screen.queryByLabelText("Origin")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Find routes/i })).not.toBeInTheDocument();
  });

  it("opens Support, closes with Escape, and restores focus", async () => {
    const user = userEvent.setup();
    render(<AppShell><p>Page</p></AppShell>);
    const trigger = screen.getByRole("button", { name: "Open support" });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "How can we help?" })).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("opens Emergency Assistance from the header with a disclaimer and restores focus", async () => {
    const user = userEvent.setup();
    render(<AppShell><p>Page</p></AppShell>);
    const trigger = screen.getByRole("button", { name: "Emergency" });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "Need immediate support?" })).toBeInTheDocument();
    expect(screen.getByText(/does not operate emergency services/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Call emergency services" })).toBeDisabled();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Need immediate support?" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("supports keyboard tab switching and an honest empty Current Trip", async () => {
    const user = userEvent.setup();
    render(<RoutePlannerPage />);
    const planTab = screen.getByRole("tab", { name: "Plan your journey" });
    planTab.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Current trip" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "No active trip" })).toBeInTheDocument();
  });

  it("requires explicit Start journey, switches to Current trip, and returns on End trip", async () => {
    const user = userEvent.setup();
    planRoute.mockResolvedValue({ recommended_route_identifier: "calm-route", routes: [plannedRoute] });
    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: "Find routes" }));
    const routeCard = await screen.findByRole("button", { name: /Select route 1, calm-route/i });
    expect(screen.queryByRole("button", { name: "End trip" })).not.toBeInTheDocument();
    await user.click(routeCard);
    expect(screen.getByText(/Selecting a route does not start your trip/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Start journey" }));
    expect(screen.getByRole("tab", { name: "Current trip" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Bourke Street Mall, Melbourne VIC")).toBeInTheDocument();
    expect(screen.getByText("Flinders Street Station, Melbourne VIC")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "End trip" }));
    expect(screen.getByRole("tab", { name: "Plan your journey" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("dialog", { name: "How was your journey?" })).toBeInTheDocument();
  });

  it("submits concise journey feedback and supports accessible ratings", async () => {
    const user = userEvent.setup();
    planRoute.mockResolvedValue({ recommended_route_identifier: "calm-route", routes: [plannedRoute] });
    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: "Find routes" }));
    await user.click(await screen.findByRole("button", { name: /Select route 1, calm-route/i }));
    await user.click(screen.getByRole("button", { name: "Start journey" }));
    await user.click(screen.getByRole("button", { name: "End trip" }));
    await user.click(screen.getByRole("button", { name: "Sensory comfort: 5 of 5" }));
    await user.click(screen.getByRole("button", { name: "Crowd comfort: 4 of 5" }));
    await user.type(screen.getByRole("textbox", { name: "Optional comment" }), "Calm and clear");
    await user.click(screen.getByRole("button", { name: "Submit feedback" }));
    await waitFor(() => expect(submitJourneyFeedback).toHaveBeenCalledWith({ route_id: 14, sensory_rating: 5, crowd_rating: 4, comments: "Calm and clear" }));
    expect(await screen.findByText(/feedback was submitted/)).toBeInTheDocument();
  });

  it("switches between Map and Details without changing the selected route", async () => {
    const user = userEvent.setup();
    planRoute.mockResolvedValue({ recommended_route_identifier: "calm-route", routes: [plannedRoute] });
    render(<RoutePlannerPage />);
    await user.click(screen.getByRole("button", { name: "Find routes" }));
    await user.click(await screen.findByRole("button", { name: /Select route 1, calm-route/i }));
    await user.click(screen.getByRole("tab", { name: "Details" }));
    expect(screen.getByRole("tab", { name: "Details" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByText(/calm-route selected/)).not.toHaveLength(0);
    expect(planRoute).toHaveBeenCalledTimes(1);
  });

  it("offers keyboard-selectable local suggestions and preserves manual typing without a key", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(<JourneyForm onSubmit={onSubmit} loading={false} />);
    const origin = screen.getByRole("combobox", { name: "Origin" });
    await user.clear(origin);
    await user.type(origin, "State");
    await user.keyboard("{ArrowDown}{Enter}");
    expect(origin).toHaveValue("State Library Victoria");
    await user.clear(origin);
    await user.type(origin, "Unknown place");
    expect(origin).toHaveValue("Unknown place");
    expect(screen.getByText(/Google location suggestions are unavailable/)).toBeInTheDocument();
  });

  it("keeps manual origin available after location permission denial", async () => {
    const user = userEvent.setup();
    Object.defineProperty(globalThis.navigator, "geolocation", { configurable: true, value: { getCurrentPosition: (success, failure) => failure({ code: 1, PERMISSION_DENIED: 1 }) } });
    render(<JourneyForm onSubmit={() => {}} loading={false} />);
    await user.click(screen.getByRole("button", { name: "Use current location" }));
    expect(screen.getByText(/permission was denied/)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Origin" })).toBeEnabled();
  });

  it("renders all Settings sections and applies accessibility preferences locally", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);
    ["Sensory preferences", "Journey preferences", "Notifications", "Accessibility", "Privacy"].forEach((name) => expect(screen.getByRole("heading", { name })).toBeInTheDocument());
    await user.click(screen.getByRole("checkbox", { name: "Larger text" }));
    expect(document.documentElement).toHaveClass("larger-text");
    expect(screen.getByText(/not permanently saved/)).toBeInTheDocument();
  });
});
