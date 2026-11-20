"""API routes for KrishiRate prices.

Endpoints:
    GET  /prices/today?crop=&district=&market=
    GET  /prices/trend?crop=&market=&days=30
    GET  /prices/compare?crop=&district=
    GET  /markets?district=
    POST /prices/refresh
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Price
from ..services.sync_service import sync_prices

router = APIRouter()


def _require(value: Optional[str], name: str) -> str:
    """Return value or raise 422 if missing/blank."""
    if not value or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required query parameter: {name}",
        )
    return value.strip()


@router.get("/prices/today")
def prices_today(
    crop: str = Query(None),
    district: str = Query(None),
    market: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Latest available prices for a crop in a district (optionally one market)."""
    crop = _require(crop, "crop")
    district = _require(district, "district")

    latest_date = db.query(func.max(Price.date)).scalar()
    if latest_date is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price data available. Call POST /prices/refresh first.",
        )

    query = db.query(Price).filter(
        Price.crop == crop,
        Price.district == district,
        Price.date == latest_date,
    )
    if market:
        query = query.filter(Price.market == market.strip())

    results = query.all()
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No prices found for {crop} in {district}"
            + (f" at {market}" if market else ""),
        )

    return {"date": latest_date.isoformat(), "prices": [r.to_dict() for r in results]}


@router.get("/prices/trend")
def prices_trend(
    crop: str = Query(None),
    market: str = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Price trend for a crop at a market over the last ``days`` days."""
    crop = _require(crop, "crop")
    market = _require(market, "market")

    latest_date = db.query(func.max(Price.date)).filter(
        Price.crop == crop, Price.market == market
    ).scalar()
    if latest_date is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data for {crop} at {market}.",
        )

    start_date = latest_date - timedelta(days=days - 1)
    results = (
        db.query(Price)
        .filter(
            Price.crop == crop,
            Price.market == market,
            Price.date >= start_date,
            Price.date <= latest_date,
        )
        .order_by(Price.date.asc())
        .all()
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trend data for {crop} at {market} in the last {days} days.",
        )

    return {
        "crop": crop,
        "market": market,
        "days": days,
        "start_date": start_date.isoformat(),
        "end_date": latest_date.isoformat(),
        "prices": [r.to_dict() for r in results],
    }


@router.get("/prices/compare")
def prices_compare(
    crop: str = Query(None),
    district: str = Query(None),
    db: Session = Depends(get_db),
):
    """Compare prices across all markets for a crop in a district (latest date)."""
    crop = _require(crop, "crop")
    district = _require(district, "district")

    latest_date = db.query(func.max(Price.date)).filter(
        Price.crop == crop, Price.district == district
    ).scalar()
    if latest_date is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data for {crop} in {district}.",
        )

    results = (
        db.query(Price)
        .filter(
            Price.crop == crop,
            Price.district == district,
            Price.date == latest_date,
        )
        .order_by(Price.modal_price.desc().nullslast())
        .all()
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No prices to compare for {crop} in {district}.",
        )

    return {
        "date": latest_date.isoformat(),
        "markets": [r.to_dict() for r in results],
    }


@router.get("/markets")
def markets(district: str = Query(None), db: Session = Depends(get_db)):
    """List distinct markets that have price data for a district."""
    district = _require(district, "district")

    results = (
        db.query(Price.market, Price.state)
        .filter(Price.district == district)
        .distinct()
        .order_by(Price.market.asc())
        .all()
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No markets found for district {district}.",
        )

    return {
        "district": district,
        "markets": [{"market": r[0], "state": r[1]} for r in results],
    }


@router.post("/prices/refresh")
def prices_refresh(
    crop: str = Query("Arecanut"),
    district: str = Query("Dakshina Kannada"),
    db: Session = Depends(get_db),
):
    """Fetch new mandi prices (API first, CSV fallback) and store them."""
    summary = sync_prices(db, crop, district)
    return {"status": "ok", **summary}
