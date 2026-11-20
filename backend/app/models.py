"""SQLAlchemy models for KrishiRate.

Defines the ``Price`` table used to store daily mandi price records.
"""

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, UniqueConstraint, Boolean

from .database import Base


class Price(Base):
    """Daily mandi price for a crop at a specific market."""

    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    crop = Column(String, nullable=False, index=True)
    state = Column(String, nullable=False)
    district = Column(String, nullable=False, index=True)
    market = Column(String, nullable=False, index=True)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    modal_price = Column(Float, nullable=True)
    date = Column(Date, nullable=False, index=True)

    # Never store duplicate records for the same crop, market, and date.
    __table_args__ = (UniqueConstraint("crop", "market", "date", name="uq_crop_market_date"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "crop": self.crop,
            "state": self.state,
            "district": self.district,
            "market": self.market,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "modal_price": self.modal_price,
            "date": self.date.isoformat() if self.date else None,
        }


class Alert(Base):
    """Price alert for a Telegram chat.

    Triggers when the latest modal price for a crop/district/market meets the
    configured condition (above/below the target price).
    """

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, nullable=False, index=True)
    crop = Column(String, nullable=False, index=True)
    district = Column(String, nullable=False, index=True)
    market = Column(String, nullable=True)
    target_price = Column(Float, nullable=False)
    condition = Column(String, nullable=False)  # "above" or "below"
    active = Column(Boolean, default=True, nullable=False)
    last_triggered_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "crop": self.crop,
            "district": self.district,
            "market": self.market,
            "target_price": self.target_price,
            "condition": self.condition,
            "active": self.active,
            "last_triggered_at": self.last_triggered_at.isoformat()
            if self.last_triggered_at
            else None,
        }
