"""Sync service: fetch mandi prices and persist them to SQLite.

Reuses :mod:`backend.app.services.mandi_service` for fetching (API first,
CSV fallback) and skips rows that already exist thanks to the unique
constraint on ``(crop, market, date)``.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .mandi_service import fetch_prices
from ..database import SessionLocal
from ..models import Price

# Last successful sync/refresh timestamp (ISO format), set by sync_prices.
LAST_REFRESH_AT: Optional[str] = None


def _row_to_model(row: dict) -> Price:
    """Convert a normalized price record into a Price ORM instance."""
    date_str = row.get("arrival_date") or datetime.utcnow().date().isoformat()
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        date_obj = datetime.utcnow().date()

    return Price(
        crop=row.get("commodity", ""),
        state=row.get("state", ""),
        district=row.get("district", ""),
        market=row.get("market", ""),
        min_price=row.get("min_price"),
        max_price=row.get("max_price"),
        modal_price=row.get("modal_price"),
        date=date_obj,
    )


def sync_prices(db: Session, commodity: str, district: str) -> dict:
    """Fetch prices for one crop/district and save new rows to the DB.

    Rows that already exist (same crop, market, date) are skipped silently
    thanks to the unique constraint.

    Returns a summary dict: ``{"fetched": N, "inserted": N, "skipped": N,
    "source": str}``.
    """
    global LAST_REFRESH_AT
    prices, source = fetch_prices(commodity, district)
    fetched = len(prices)
    inserted = 0
    skipped = 0

    for row in prices:
        model = _row_to_model(row)
        try:
            db.add(model)
            db.commit()
            db.refresh(model)
            inserted += 1
        except IntegrityError:
            # Duplicate (crop, market, date) - skip it.
            db.rollback()
            skipped += 1

    LAST_REFRESH_AT = datetime.now(timezone.utc).isoformat()

    return {
        "fetched": fetched,
        "inserted": inserted,
        "skipped": skipped,
        "source": source,
    }


def sync_prices_default(db: Session) -> dict:
    """Convenience wrapper using the default crop and district."""
    return sync_prices(db, "Arecanut", "Dakshina Kannada")
