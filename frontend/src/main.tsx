import React from "react";
import ReactDOM from "react-dom/client";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  MapPin,
  Navigation,
  RefreshCw,
  Route,
  ShieldCheck,
} from "lucide-react";
import axios from "axios";
import "./styles.css";

type CrowdThreshold = "low" | "medium" | "high";

type SensorLocation = {
  sensor_id: number;
  sensor_name: string;
  sensor_description: string | null;
  latitude: number;
  longitude: number;
  status: string;
  location_type: string | null;
};

type SensorLocationsResponse = {
  sensors: SensorLocation[];
  count: number;
  source: string;
};

type LiveCrowdSummary = {
  total_readings: number;
  low_count: number;
  medium_count: number;
  high_count: number;
};

type LatestCountsResponse = {
  count: number;
  summary: LiveCrowdSummary;
  source: string;
  data_note: string;
};

type RoutePlanResponse = {
  status: string;
  message: string;
  requested_threshold: CrowdThreshold;
  data_confidence: string;
  limitations: string[];
  routes: RouteOption[];
  destination: Coordinate | null;
};

type Coordinate = {
  latitude: number;
  longitude: number;
};

type SensoryRefuge = {
  name: string;
  theme: string | null;
  sub_theme: string | null;
  latitude: number;
  longitude: number;
  distance_m: number | null;
  data_note: string;
};

type NearbyRefugesResponse = {
  refuges: SensoryRefuge[];
  count: number;
  source: string;
  data_note: string;
};

type RouteOption = {
  route_id: string;
  title: string;
  summary: string;
  distance_m: number;
  estimated_duration_min: number;
  sensory_level: CrowdThreshold;
  high_congestion_segments: number;
  medium_congestion_segments: number;
  sensor_coverage: string;
  matched_sensor_count: number;
  average_pedestrian_count: number | null;
  max_pedestrian_count: number | null;
  data_source: string;
  recommendation_reason: string;
  is_recommended: boolean;
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000",
  timeout: 12000,
});

const thresholdCopy: Record<CrowdThreshold, string> = {
  low: "Prefer the calmest available option and warn early.",
  medium: "Balance calmer streets with a practical walking route.",
  high: "Allow busier areas if they make the trip more direct.",
};

const melbourneBounds = {
  minLat: -37.826,
  maxLat: -37.796,
  minLng: 144.94,
  maxLng: 144.982,
};

function App() {
  const [origin, setOrigin] = React.useState("Flinders Street Station");
  const [destination, setDestination] = React.useState("State Library Victoria");
  const [threshold, setThreshold] = React.useState<CrowdThreshold>("medium");
  const [sensors, setSensors] = React.useState<SensorLocation[]>([]);
  const [liveCrowd, setLiveCrowd] = React.useState<LatestCountsResponse | null>(null);
  const [refuges, setRefuges] = React.useState<NearbyRefugesResponse | null>(null);
  const [sensorStatus, setSensorStatus] = React.useState<"idle" | "loading" | "ready" | "error">("idle");
  const [crowdStatus, setCrowdStatus] = React.useState<"idle" | "loading" | "ready" | "error">("idle");
  const [routeStatus, setRouteStatus] = React.useState<"idle" | "loading" | "ready" | "error">("idle");
  const [refugeStatus, setRefugeStatus] = React.useState<"idle" | "loading" | "ready" | "error">("idle");
  const [routeResult, setRouteResult] = React.useState<RoutePlanResponse | null>(null);
  const [errorMessage, setErrorMessage] = React.useState("");

  const activeSensors = sensors.filter((sensor) => sensor.status === "A");
  const recommendedRoute = routeResult?.routes.find((route) => route.is_recommended);
  const coverageLabel =
    activeSensors.length > 70 ? "strong" : activeSensors.length > 25 ? "partial" : "limited";

  React.useEffect(() => {
    void loadSensors();
    void loadLiveCrowd();
  }, []);

  async function loadSensors() {
    setSensorStatus("loading");
    setErrorMessage("");
    try {
      const response = await api.get<SensorLocationsResponse>("/api/crowd/sensor-locations");
      setSensors(response.data.sensors);
      setSensorStatus("ready");
    } catch {
      setSensorStatus("error");
      setErrorMessage("Sensor locations could not be loaded. You can still validate a journey request.");
    }
  }

  async function loadLiveCrowd() {
    setCrowdStatus("loading");
    try {
      const response = await api.get<LatestCountsResponse>("/api/crowd/latest-counts");
      setLiveCrowd(response.data);
      setCrowdStatus("ready");
    } catch {
      setCrowdStatus("error");
      setLiveCrowd(null);
    }
  }

  async function planJourney(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRouteStatus("loading");
    setRouteResult(null);
    setErrorMessage("");

    try {
      const response = await api.post<RoutePlanResponse>("/api/routes/plan", {
        origin: { label: origin },
        destination: { label: destination },
        crowd_threshold: threshold,
      });
      setRouteResult(response.data);
      setRouteStatus("ready");
      if (response.data.destination) {
        void loadNearbyRefuges(response.data.destination);
      }
    } catch {
      setRouteStatus("error");
      setErrorMessage("The journey request could not be validated. Check the locations and try again.");
    }
  }

  async function loadNearbyRefuges(coordinates: Coordinate) {
    setRefugeStatus("loading");
    setRefuges(null);
    try {
      const response = await api.get<NearbyRefugesResponse>("/api/crowd/refuges/nearby", {
        params: {
          latitude: coordinates.latitude,
          longitude: coordinates.longitude,
          limit: 5,
        },
      });
      setRefuges(response.data);
      setRefugeStatus("ready");
    } catch {
      setRefugeStatus("error");
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="planner-panel" aria-label="Journey planner">
          <div className="brand-row">
            <div className="brand-mark">
              <Navigation size={22} aria-hidden="true" />
            </div>
            <div>
              <p className="eyebrow">Melbourne CBD</p>
              <h1>eScape</h1>
            </div>
          </div>

          <form className="journey-form" onSubmit={planJourney}>
            <label>
              <span>Start</span>
              <input value={origin} onChange={(event) => setOrigin(event.target.value)} required maxLength={180} />
            </label>
            <label>
              <span>Destination</span>
              <input
                value={destination}
                onChange={(event) => setDestination(event.target.value)}
                required
                maxLength={180}
              />
            </label>

            <fieldset>
              <legend>Maximum crowd level I am comfortable with</legend>
              <div className="segmented-control">
                {(["low", "medium", "high"] as CrowdThreshold[]).map((level) => (
                  <button
                    className={threshold === level ? "active" : ""}
                    key={level}
                    onClick={() => setThreshold(level)}
                    type="button"
                    title={thresholdCopy[level]}
                  >
                    {level}
                  </button>
                ))}
              </div>
              <p>{thresholdCopy[threshold]}</p>
            </fieldset>

            <button className="primary-action" type="submit" disabled={routeStatus === "loading"}>
              {routeStatus === "loading" ? <Loader2 className="spin" size={18} /> : <Route size={18} />}
              Plan Journey
            </button>
          </form>

          <div className="status-strip">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>Backend validation is active. Live routing and scoring are the next connection points.</span>
          </div>
        </aside>

        <section className="map-panel" aria-label="Sensor map">
          <div className="map-header">
            <div>
              <p className="eyebrow">Crowd Data Layer</p>
              <h2>Pedestrian Sensor Coverage</h2>
            </div>
            <button className="icon-button" onClick={loadSensors} type="button" title="Refresh sensor locations">
              {sensorStatus === "loading" ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
            </button>
          </div>

          <div className="sensor-map">
            {activeSensors.slice(0, 120).map((sensor) => (
              <span
                className="sensor-dot"
                key={sensor.sensor_id}
                style={sensorPosition(sensor)}
                title={`${sensor.sensor_description ?? sensor.sensor_name} (${sensor.sensor_name})`}
              />
            ))}
            <div className="route-preview-line" />
            <div className="map-label origin">
              <MapPin size={14} />
              Start
            </div>
            <div className="map-label destination">
              <MapPin size={14} />
              Destination
            </div>
          </div>

          <div className="insight-grid">
            <StatusMetric label="Sensor records" value={sensorStatus === "ready" ? String(sensors.length) : "--"} />
            <StatusMetric label="Active sensors" value={sensorStatus === "ready" ? String(activeSensors.length) : "--"} />
            <StatusMetric label="Coverage confidence" value={sensorStatus === "ready" ? coverageLabel : "unknown"} />
          </div>

          <div className="live-crowd-panel">
            <div className="live-crowd-header">
              <div>
                <p className="eyebrow">Past Hour Counts</p>
                <h3>Live Crowd Snapshot</h3>
              </div>
              <button className="icon-button compact" onClick={loadLiveCrowd} type="button" title="Refresh live counts">
                {crowdStatus === "loading" ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
              </button>
            </div>
            <div className="crowd-bars">
              <CrowdBar label="Low" value={liveCrowd?.summary.low_count ?? 0} total={liveCrowd?.summary.total_readings ?? 0} tone="low" />
              <CrowdBar
                label="Medium"
                value={liveCrowd?.summary.medium_count ?? 0}
                total={liveCrowd?.summary.total_readings ?? 0}
                tone="medium"
              />
              <CrowdBar label="High" value={liveCrowd?.summary.high_count ?? 0} total={liveCrowd?.summary.total_readings ?? 0} tone="high" />
            </div>
            <p className="data-note">
              {crowdStatus === "ready"
                ? liveCrowd?.data_note
                : crowdStatus === "error"
                  ? "Live crowd counts could not be loaded. Missing data remains unknown."
                  : "Loading live pedestrian counts."}
            </p>
          </div>
        </section>

        <section className="results-panel" aria-label="Route results">
          <div className="results-header">
            <p className="eyebrow">Route Assessment</p>
            <h2>Journey Readiness</h2>
          </div>

          {routeResult ? (
            <div className="result-state success">
              <CheckCircle2 size={22} aria-hidden="true" />
              <div>
                <h3>{recommendedRoute ? recommendedRoute.title : "Routes planned"}</h3>
                <p>{routeResult.message}</p>
                <dl>
                  <div>
                    <dt>Start</dt>
                    <dd>{origin}</dd>
                  </div>
                  <div>
                    <dt>Destination</dt>
                    <dd>{destination}</dd>
                  </div>
                  <div>
                    <dt>Crowd threshold</dt>
                    <dd>{routeResult.requested_threshold}</dd>
                  </div>
                  <div>
                    <dt>Data confidence</dt>
                    <dd>{routeResult.data_confidence}</dd>
                  </div>
                </dl>
              </div>
            </div>
          ) : (
            <div className="result-state">
              <AlertTriangle size={22} aria-hidden="true" />
              <div>
                <h3>No route calculated yet</h3>
                <p>
                  Submit a journey to validate the request. The app currently shows sensor coverage, then routing and
                  scoring will be connected next.
                </p>
              </div>
            </div>
          )}

          {errorMessage ? <p className="error-message">{errorMessage}</p> : null}

          {routeResult?.routes.length ? (
            <div className="route-list">
              {routeResult.routes.map((route) => (
                <article className={`route-card ${route.is_recommended ? "recommended" : ""}`} key={route.route_id}>
                  <div className="route-card-header">
                    <div>
                      <h3>{route.title}</h3>
                      <p>{route.summary}</p>
                    </div>
                    <span className={`level-pill ${route.sensory_level}`}>{route.sensory_level}</span>
                  </div>
                  <div className="route-stats">
                    <span>{formatDistance(route.distance_m)}</span>
                    <span>{route.estimated_duration_min} min</span>
                    <span>{route.matched_sensor_count} sensors</span>
                  </div>
                  <div className="route-stats secondary">
                    <span>max {route.max_pedestrian_count ?? "--"}</span>
                    <span>avg {route.average_pedestrian_count ?? "--"}</span>
                    <span>{route.sensor_coverage} coverage</span>
                  </div>
                  <p className="route-reason">{route.recommendation_reason}</p>
                  <p className="route-source">{route.data_source}</p>
                  {route.is_recommended ? <strong className="recommended-label">Recommended</strong> : null}
                </article>
              ))}
            </div>
          ) : null}

          {routeResult?.limitations.length ? (
            <div className="limitations">
              <h3>Data limits</h3>
              <ul>
                {routeResult.limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="refuge-panel">
            <div className="results-header">
              <div>
                <p className="eyebrow">Sensory Refuges</p>
                <h2>Nearby Quiet Stops</h2>
              </div>
            </div>
            {refugeStatus === "idle" ? (
              <p className="data-note">Plan a journey to search for refuge candidates near the destination.</p>
            ) : refugeStatus === "loading" ? (
              <p className="data-note">Loading nearby refuge candidates.</p>
            ) : refugeStatus === "error" ? (
              <p className="error-message">Refuge candidates could not be loaded right now.</p>
            ) : refuges?.refuges.length ? (
              <>
                <div className="refuge-list">
                  {refuges.refuges.map((refuge) => (
                    <article className="refuge-card" key={`${refuge.name}-${refuge.latitude}-${refuge.longitude}`}>
                      <div>
                        <h3>{refuge.name}</h3>
                        <p>{refuge.sub_theme ?? refuge.theme ?? "Point of interest"}</p>
                      </div>
                      <strong>{refuge.distance_m !== null ? formatDistance(refuge.distance_m) : "nearby"}</strong>
                    </article>
                  ))}
                </div>
                <p className="data-note">{refuges.data_note}</p>
              </>
            ) : (
              <p className="data-note">No refuge candidates were returned near this destination.</p>
            )}
          </div>

          <div className="next-steps">
            <h3>Current MVP status</h3>
            <ul>
              <li>Sensor locations load from City of Melbourne Open Data.</li>
              <li>Journey inputs return deterministic MVP route options.</li>
              <li>Nearby refuge candidates load from City landmarks/POIs.</li>
              <li>Map markers are schematic until real map routing is connected.</li>
              <li>Route sensory levels are explainable assumptions until live per-segment scoring is connected.</li>
            </ul>
          </div>
        </section>
      </section>
    </main>
  );
}

function sensorPosition(sensor: SensorLocation): React.CSSProperties {
  const x = ((sensor.longitude - melbourneBounds.minLng) / (melbourneBounds.maxLng - melbourneBounds.minLng)) * 100;
  const y = ((melbourneBounds.maxLat - sensor.latitude) / (melbourneBounds.maxLat - melbourneBounds.minLat)) * 100;

  return {
    left: `${clamp(x, 3, 97)}%`,
    top: `${clamp(y, 3, 97)}%`,
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function formatDistance(distanceM: number) {
  if (distanceM >= 1000) {
    return `${(distanceM / 1000).toFixed(1)} km`;
  }
  return `${distanceM} m`;
}

function StatusMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CrowdBar({
  label,
  value,
  total,
  tone,
}: {
  label: string;
  value: number;
  total: number;
  tone: CrowdThreshold;
}) {
  const width = total > 0 ? Math.max(4, Math.round((value / total) * 100)) : 0;

  return (
    <div className="crowd-bar">
      <div className="crowd-bar-row">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="bar-track">
        <span className={`bar-fill ${tone}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
