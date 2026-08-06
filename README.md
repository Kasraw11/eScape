# eScape

eScape brings route and sensory information together to help users identify calmer Melbourne CBD routes, receive warnings about potential stressors, and locate calmer alternatives.

## Environment

Backend `.env` values:

```env
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@localhost:5432/escape_db
GOOGLE_MAPS_API_KEY=
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
```

Frontend `.env` values:

```env
NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY=
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Backend

```powershell
cd "E:\FIT 5120\Onboarding\eScape\backend"
py -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend

```powershell
cd "E:\FIT 5120\Onboarding\eScape\frontend"
npm install
npm run dev
```

Open `http://localhost:3000`.

## Testing

```powershell
cd "E:\FIT 5120\Onboarding\eScape\backend"
python -m unittest discover -s tests

cd "E:\FIT 5120\Onboarding\eScape\frontend"
npm run lint
npm test
npm run build
```
