import os
from dotenv import load_dotenv

load_dotenv()

# Data.gov.in Open Data API key (Agmarknet dataset)
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "")

# data.gov.in Agmarknet resource ID (override if your key maps to a different one)
DATA_GOV_RESOURCE_ID = os.getenv(
    "DATA_GOV_RESOURCE_ID", "9ef8426c-d546-49ea-a7cf-19c79e35c7d7"
)

# Telegram bot settings for price alerts
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Backend settings
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# SQLite database file lives in the data/ folder at the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATABASE_URL = os.getenv(
    "KRISHI_DATABASE_URL",
    "sqlite:///" + os.path.join(BASE_DIR, "data", "krishirate.db"),
)

# Normalize Render-style "postgres://" URLs to SQLAlchemy's
# "postgresql+psycopg2://" so psycopg2 is used as the driver.
if _DATABASE_URL.startswith("postgres://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

DATABASE_URL = _DATABASE_URL

# Alert cooldown window (hours) before re-sending the same alert
ALERT_COOLDOWN_HOURS = int(os.getenv("ALERT_COOLDOWN_HOURS", "24"))

# Background alert job interval (hours)
ALERT_JOB_INTERVAL_HOURS = int(os.getenv("ALERT_JOB_INTERVAL_HOURS", "6"))

# Simple rate limit: max requests per window per IP (applied to POST endpoints)
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
