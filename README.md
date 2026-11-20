# KrishiRate

KrishiRate helps Karnataka farmers check today's crop prices in nearby
markets (mandis) using the Government of India Open Data API (data.gov.in,
Agmarknet dataset). Falls back to a local sample CSV when the API is down.

## Folder structure

- `backend/` - Python FastAPI app (API endpoints, database, data fetching)
  - `app/main.py` - FastAPI app + health check
  - `app/config.py` - reads settings from `.env`
  - `app/database.py` - SQLite engine, session, `create_tables()`
  - `app/models.py` - `Price` SQLAlchemy model
  - `app/services/mandi_service.py` - fetch prices (API first, CSV fallback)
  - `app/services/sync_service.py` - fetch + save prices to SQLite
  - `app/api/prices.py` - all price/market endpoints
  - `app/api/` - route modules
- `frontend/` - Simple HTML/CSS/JS UI with Chart.js (no heavy frameworks)
- `data/` - Fallback sample CSV and the SQLite database
- `tests/` - Automated pytest tests

## Setup (Steps 1-3)

1. Create a virtual environment:

```powershell
python -m venv venv
```

2. Activate it:

```powershell
venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Copy the example env file and add your API keys:

```powershell
copy .env.example .env
```

Then edit `.env` and paste your `DATA_GOV_API_KEY` from data.gov.in.

5. Run the backend:

```powershell
uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000/health to confirm it works.

6. Run the tests:

```powershell
pytest
```

## API endpoints

All endpoints live under `backend/app/api/prices.py`.

### GET /prices/today
Latest available prices for a crop in a district (optionally one market).

Query params: `crop` (required), `district` (required), `market` (optional)

```powershell
curl "http://127.0.0.1:8000/prices/today?crop=Arecanut&district=Dakshina%20Kannada"
curl "http://127.0.0.1:8000/prices/today?crop=Arecanut&district=Dakshina%20Kannada&market=Mangalore"
```

### GET /prices/trend
Price trend for a crop at a market over the last N days (default 30).

Query params: `crop` (required), `market` (required), `days` (optional, 1-365)

```powershell
curl "http://127.0.0.1:8000/prices/trend?crop=Arecanut&market=Mangalore&days=30"
```

### GET /prices/compare
Compare prices across all markets for a crop in a district (latest date).

Query params: `crop` (required), `district` (required)

```powershell
curl "http://127.0.0.1:8000/prices/compare?crop=Arecanut&district=Dakshina%20Kannada"
```

### GET /markets
List distinct markets that have price data for a district.

Query params: `district` (required)

```powershell
curl "http://127.0.0.1:8000/markets?district=Dakshina%20Kannada"
```

### POST /prices/refresh
Fetch new mandi prices (API first, CSV fallback) and store them.

Query params: `crop` (optional, default Arecanut), `district` (optional, default Dakshina Kannada)

```powershell
curl -X POST "http://127.0.0.1:8000/prices/refresh?crop=Arecanut&district=Dakshina%20Kannada"
```

### Price Alerts (Telegram)

All alert endpoints live under `backend/app/api/alerts.py`. Configure
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` before using alerts.

#### POST /alerts
Create a price alert for a Telegram chat.

Query params: `chat_id` (required), `crop` (required), `district` (required),
`market` (optional), `target_price` (required), `condition` (optional, `above`
or `below`, default `above`).

```powershell
curl -X POST "http://127.0.0.1:8000/alerts?chat_id=12345&crop=Arecanut&district=Dakshina%20Kannada&target_price=420&condition=above"
```

#### GET /alerts?chat_id=
List all alerts for a Telegram chat id.

```powershell
curl "http://127.0.0.1:8000/alerts?chat_id=12345"
```

#### DELETE /alerts/{id}
Delete an alert by id.

```powershell
curl -X DELETE "http://127.0.0.1:8000/alerts/1"
```

#### POST /alerts/test
Send a test message to the configured Telegram chat.

```powershell
curl -X POST "http://127.0.0.1:8000/alerts/test"
```

#### POST /alerts/price
Fetch the latest price and send it as a Telegram alert.

Query params: `crop` (required), `district` (required), `market` (optional).

#### Background alert job
An APScheduler background job runs every 6 hours: it refreshes prices
(API first, CSV fallback), checks every active alert against the latest modal
price, and sends a Telegram message when the condition is met. An alert is not
re-sent within a 24-hour cooldown window (`last_triggered_at`).

### Error responses
- `404` - no data found for the given query
- `422` - missing or invalid input (e.g. required query param absent)

## Next steps

Steps completed: frontend UI, market comparison view, Telegram price
alerts, and a Kannada language toggle.

Remaining: additional crops/districts, multi-language refinement.

## How it works

1. **Data fetching** — `backend/app/services/mandi_service.py` queries the
   Government of India Open Data API (data.gov.in, Agmarknet dataset) for
   today's mandi prices. If the API is unavailable or misconfigured, it falls
   back to the local sample CSV in `data/sample_prices.csv`.
2. **Sync** — `backend/app/services/sync_service.py` fetches prices and
   persists them to SQLite, skipping duplicates via a unique constraint on
   `(crop, market, date)`.
3. **API** — FastAPI endpoints (`backend/app/api/prices.py`) serve today's
   prices, trends, market comparisons, market lists, and price refresh.
4. **Alerts** — `backend/app/services/alert_service.py` runs on an
   APScheduler interval (default 6h): refreshes prices, checks every active
   alert against the latest modal price, and sends a Telegram message when
   the condition (above/below target) is met. A 24-hour cooldown prevents
   re-sending the same alert.
5. **Frontend** — Plain HTML/CSS/JS UI (`frontend/`) with Chart.js for the
   30-day trend, a market comparison table, i18n (English/Kannada), and a
   "Set Alert" form.

## Screenshots

<!-- Add screenshots here -->
- ![Home page](./docs/screenshots/home.png)
- ![Market comparison](./docs/screenshots/compare.png)
- ![Set Alert form](./docs/screenshots/alert.png)
- ![Kannada toggle](./docs/screenshots/kannada.png)

## Deployment

### Environment variables

Copy `.env.example` to `.env` and fill in your values. Never commit `.env`.

| Variable | Description | Default |
|----------|-------------|---------|
| `DATA_GOV_API_KEY` | data.gov.in API key (required for live prices) | `` |
| `DATA_GOV_RESOURCE_ID` | Agmarknet resource ID | `9ef8426c-...` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for alerts | `` |
| `TELEGRAM_CHAT_ID` | Telegram chat id for alerts | `` |
| `KRISHI_DATABASE_URL` | Database URL (SQLite default; PostgreSQL supported) | `sqlite:///data/krishirate.db` |
| `API_HOST` | Bind host | `127.0.0.1` |
| `API_PORT` | Bind port | `8000` |
| `ALERT_COOLDOWN_HOURS` | Alert re-send cooldown (hours) | `24` |
| `ALERT_JOB_INTERVAL_HOURS` | Background alert job interval (hours) | `6` |
| `RATE_LIMIT_REQUESTS` | Max POST requests per window per IP | `30` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window (seconds) | `60` |

### Local development

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env and add your DATA_GOV_API_KEY
uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000/health to confirm it works.

### Docker

```powershell
docker build -t krishirate .
docker run -p 8000:8000 --env-file .env krishirate
```

The container listens on `$PORT` (default `8000`) and binds to `0.0.0.0`.

### Render

Connect this repo in Render and use the included `render.yaml`. Set the
required secrets (`DATA_GOV_API_KEY`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`) in the Render dashboard environment variables — do not
commit them.

### Railway / Heroku-style (Procfile)

```powershell
pip install -r requirements.txt
# set env vars, then:
web: uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Health check

`GET /health` reports `status`, the configured `database` URL, the last
successful `last_source` (`data.gov.in API` or `sample CSV (fallback)`), and
the last `last_refresh_at` timestamp (ISO 8601).

### Using PostgreSQL (Render free tier)

KrishiRate works with SQLite by default (single instance, file-based). For
multi-instance deployments or a managed database, use PostgreSQL:

1. In Render, create a **PostgreSQL** database (free tier available).
2. Attach it to the `krishirate` web service. Render injects `DATABASE_URL`
   automatically.
3. Set `KRISHI_DATABASE_URL = ${DATABASE_URL}` in the service environment
   (or Render will expose `DATABASE_URL`; KrishiRate reads `KRISHI_DATABASE_URL`).
4. KrishiRate normalizes Render's `postgres://` scheme to
   `postgresql+psycopg2://` and uses `psycopg2-binary` as the driver
   (already in `requirements.txt`).

No code change is required to switch from SQLite to PostgreSQL — just set
`KRISHI_DATABASE_URL`.

### Security notes

- Do not commit `.env` or any secrets (it is already in `.gitignore`).
- POST endpoints (`/prices/refresh`, `/alerts`, `/alerts/test`,
  `/alerts/price`) are rate-limited per IP to prevent abuse.
- SQLite is file-based; for multi-instance deployment, use a shared database
  or persistent volume for `data/krishirate.db`.
