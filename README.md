# eScape
eScape brings route and sensory information together to help users identify calmer routes, receive warnings about potential stressors and locate nearby quiet spaces.

## Backend Foundation

The current backend foundation uses FastAPI with the existing MySQL database setup.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check:

```bash
GET http://127.0.0.1:8000/health
```

The route-planning endpoint currently returns deterministic MVP route options for known Melbourne CBD places and scores them with nearby live pedestrian sensor readings where available. openrouteservice walking-route geometry, full per-segment scoring and refuge lookup are intentionally left for the next MVP phases.

Sensor locations can be fetched from City of Melbourne Open Data:

```bash
GET http://127.0.0.1:8000/api/crowd/sensor-locations
```

The service validates external records and skips malformed sensor rows instead of treating incomplete data as reliable.

Live past-hour pedestrian counts can also be fetched and classified:

```bash
GET http://127.0.0.1:8000/api/crowd/latest-counts
```

The endpoint keeps the latest valid reading per sensor and classifies each reading with the central low/medium/high crowd thresholds.

Nearby sensory-refuge candidates can be fetched from City landmarks/POIs:

```bash
GET http://127.0.0.1:8000/api/crowd/refuges/nearby?latitude=-37.8098&longitude=144.9652
```

Refuges are candidate quiet stops only. Opening hours, access and sensory conditions are unknown until richer data is connected.

## Frontend

The first user-facing app is a Vite React interface that talks to the FastAPI backend.

```bash
cd frontend
npm install
npm run dev
```

Open:

```bash
http://127.0.0.1:5173
```

The current UI supports route request validation, crowd preference selection, City of Melbourne pedestrian sensor coverage, a live crowd snapshot, three explainable route-option cards and nearby sensory-refuge candidates. Route cards show nearby matched sensor counts, max/average pedestrian readings and the data source. The map uses OpenStreetMap/Leaflet for interactive display; route geometry is deterministic until openrouteservice is connected.

## openrouteservice

The backend can use openrouteservice for real walking-route geometry when `OPENROUTESERVICE_API_KEY` is set.

```bash
OPENROUTESERVICE_API_KEY=your-openrouteservice-key
OPENROUTESERVICE_BASE_URL=https://api.openrouteservice.org
```

If no key is configured, the backend falls back to deterministic MVP route geometry so the app remains testable. The key is used server-side only and should not be committed.
