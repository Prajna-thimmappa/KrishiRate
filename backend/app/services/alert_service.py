"""Alert service: CRUD operations and trigger checking for price alerts.

Reuses :mod:`backend.app.services.mandi_service` / :mod:`backend.app.services.sync_service`
to refresh prices before checking every active alert against the latest modal
price. Sends a Telegram message when the condition is met and avoids re-sending
the same alert within a 24-hour cooldown window.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import ALERT_COOLDOWN_HOURS
from ..database import SessionLocal
from ..models import Alert, Price
from ..services.sync_service import sync_prices
from ..services.telegram_service import format_alert, send_message

COOLDOWN_HOURS = ALERT_COOLDOWN_HOURS


def create_alert(
    db: Session,
    chat_id: str,
    crop: str,
    district: str,
    market: Optional[str],
    target_price: float,
    condition: str,
) -> Alert:
    """Create and persist a new alert."""
    alert = Alert(
        chat_id=chat_id,
        crop=crop,
        district=district,
        market=market,
        target_price=target_price,
        condition=condition,
        active=True,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_alerts_by_chat(db: Session, chat_id: str) -> List[Alert]:
    """List all alerts for a Telegram chat id."""
    return db.query(Alert).filter(Alert.chat_id == chat_id).all()


def get_alert(db: Session, alert_id: int) -> Optional[Alert]:
    """Fetch a single alert by id."""
    return db.query(Alert).filter(Alert.id == alert_id).first()


def delete_alert(db: Session, alert_id: int) -> bool:
    """Delete an alert by id. Returns False when it does not exist."""
    alert = get_alert(db, alert_id)
    if alert is None:
        return False
    db.delete(alert)
    db.commit()
    return True


def check_and_trigger_alerts(db: Session) -> int:
    """Check every active alert against the latest price.

    Sends a Telegram message when the condition is met and stamps
    ``last_triggered_at`` so the same alert is not re-sent within the cooldown.

    Returns the number of alerts triggered.
    """
    now = datetime.utcnow()
    cooldown = timedelta(hours=COOLDOWN_HOURS)
    triggered = 0

    alerts = db.query(Alert).filter(Alert.active == True).all()  # noqa: E712
    for alert in alerts:
        # 24-hour cooldown: skip if triggered recently.
        if alert.last_triggered_at is not None:
            if now - alert.last_triggered_at < cooldown:
                continue

        latest_date = db.query(func.max(Price.date)).filter(
            Price.crop == alert.crop,
            Price.district == alert.district,
        ).scalar()
        if latest_date is None:
            continue

        query = db.query(Price).filter(
            Price.crop == alert.crop,
            Price.district == alert.district,
            Price.date == latest_date,
        )
        if alert.market:
            query = query.filter(Price.market == alert.market)
        price = query.first()
        if price is None or price.modal_price is None:
            continue

        met = False
        if alert.condition == "above" and price.modal_price > alert.target_price:
            met = True
        elif alert.condition == "below" and price.modal_price < alert.target_price:
            met = True

        if met:
            message = format_alert(
                alert.crop,
                alert.district,
                alert.market or "",
                price.to_dict(),
            )
            send_message(message)
            alert.last_triggered_at = now
            db.commit()
            triggered += 1

    return triggered


def run_alert_job() -> dict:
    """Refresh prices then check every active alert.

    Entry point for the APScheduler background job.
    """
    db = SessionLocal()
    try:
        alerts = db.query(Alert).filter(Alert.active == True).all()  # noqa: E712
        pairs = {(a.crop, a.district) for a in alerts}
        for crop, district in pairs:
            sync_prices(db, crop, district)
        triggered = check_and_trigger_alerts(db)
        return {"triggered": triggered}
    finally:
        db.close()
