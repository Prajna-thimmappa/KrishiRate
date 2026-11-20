"""API routes for Telegram price alerts.

Endpoints:
    POST  /alerts                          Create a price alert.
    GET   /alerts?chat_id=                 List alerts for a chat id.
    DELETE /alerts/{id}                    Delete an alert by id.
    POST  /alerts/test                     Send a test Telegram message.
    POST  /alerts/price?crop=&district=&market=
                                           Fetch latest price and send a Telegram alert.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Price
from ..services.alert_service import (
    create_alert,
    delete_alert,
    get_alert,
    get_alerts_by_chat,
)
from ..services.telegram_service import format_alert, send_message

router = APIRouter()


def _require(value, name):
    if not value or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required query parameter: {name}",
        )
    return value.strip()


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
def create_alert_endpoint(
    chat_id: str = Query(...),
    crop: str = Query(...),
    district: str = Query(...),
    market: Optional[str] = Query(None),
    target_price: float = Query(...),
    condition: str = Query("above"),
    db: Session = Depends(get_db),
):
    """Create a price alert for a Telegram chat."""
    condition = (condition or "above").strip().lower()
    if condition not in ("above", "below"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="condition must be 'above' or 'below'",
        )
    alert = create_alert(
        db,
        chat_id=chat_id.strip(),
        crop=crop.strip(),
        district=district.strip(),
        market=market.strip() if market else None,
        target_price=target_price,
        condition=condition,
    )
    return {"status": "ok", "alert": alert.to_dict()}


@router.get("/alerts")
def list_alerts(
    chat_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """List all alerts for a Telegram chat id."""
    chat_id = _require(chat_id, "chat_id")
    alerts = get_alerts_by_chat(db, chat_id)
    return {"chat_id": chat_id, "alerts": [a.to_dict() for a in alerts]}


@router.delete("/alerts/{alert_id}")
def delete_alert_endpoint(
    alert_id: int,
    db: Session = Depends(get_db),
):
    """Delete an alert by id."""
    if not delete_alert(db, alert_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found.",
        )
    return {"status": "ok", "deleted": alert_id}


@router.post("/alerts/test")
def alerts_test():
    """Send a test message to the configured Telegram chat."""
    ok = send_message("KrishiRate test alert: Telegram notifications are working.")
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send Telegram message. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.",
        )
    return {"status": "ok", "sent": True}


@router.post("/alerts/price")
def alerts_price(
    crop: str = Query(None),
    district: str = Query(None),
    market: str = Query(None),
    db: Session = Depends(get_db),
):
    """Fetch the latest price and send it as a Telegram alert."""
    crop = _require(crop, "crop")
    district = _require(district, "district")

    from sqlalchemy import func

    latest_date = db.query(func.max(Price.date)).filter(
        Price.crop == crop, Price.district == district
    ).scalar()
    if latest_date is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data for {crop} in {district}.",
        )

    query = db.query(Price).filter(
        Price.crop == crop,
        Price.district == district,
        Price.date == latest_date,
    )
    if market:
        query = query.filter(Price.market == market.strip())

    price = query.first()
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price found for {crop} in {district}"
            + (f" at {market}" if market else ""),
        )

    message = format_alert(crop, district, price.market or "", price.to_dict())
    ok = send_message(message)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send Telegram alert. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.",
        )

    return {
        "status": "ok",
        "sent": True,
        "date": latest_date.isoformat(),
        "price": price.to_dict(),
    }
