"""API tests for KrishiRate endpoints using a temporary test database."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models import Price


def _add_price(session: Session, crop, district, market, state, modal, mn, mx, d):
    session.add(
        Price(
            crop=crop,
            state=state,
            district=district,
            market=market,
            min_price=mn,
            max_price=mx,
            modal_price=modal,
            date=d,
        )
    )
    session.commit()


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_prices_today_404_when_empty(client: TestClient):
    response = client.get("/prices/today?crop=Arecanut&district=Dakshina Kannada")
    assert response.status_code == 404
    assert "No price data" in response.json()["detail"]


def test_prices_today(client: TestClient, session: Session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 410, 390, 430, date(2026, 11, 20))
    _add_price(session, "Arecanut", "Dakshina Kannada", "Puttur", "Karnataka", 400, 380, 420, date(2026, 11, 20))
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 380, 360, 400, date(2026, 11, 19))

    response = client.get("/prices/today?crop=Arecanut&district=Dakshina Kannada")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-11-20"
    markets = {p["market"] for p in body["prices"]}
    assert markets == {"Mangalore", "Puttur"}


def test_prices_today_market_filter(client: TestClient, session: Session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 410, 390, 430, date(2026, 11, 20))
    _add_price(session, "Arecanut", "Dakshina Kannada", "Puttur", "Karnataka", 400, 380, 420, date(2026, 11, 20))

    response = client.get(
        "/prices/today?crop=Arecanut&district=Dakshina Kannada&market=Puttur"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["prices"]) == 1
    assert body["prices"][0]["market"] == "Puttur"


def test_prices_today_market_404(client: TestClient, session: Session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 410, 390, 430, date(2026, 11, 20))

    response = client.get(
        "/prices/today?crop=Arecanut&district=Dakshina Kannada&market=Unknown"
    )
    assert response.status_code == 404


def test_prices_today_missing_params_422(client: TestClient):
    response = client.get("/prices/today?crop=Arecanut")
    assert response.status_code == 422


def test_prices_trend(client: TestClient, session: Session):
    for day in range(5):
        _add_price(
            session,
            "Arecanut",
            "Dakshina Kannada",
            "Mangalore",
            "Karnataka",
            400 + day,
            380 + day,
            420 + day,
            date(2026, 11, 20 - day),
        )

    response = client.get("/prices/trend?crop=Arecanut&market=Mangalore&days=5")
    assert response.status_code == 200
    body = response.json()
    assert body["crop"] == "Arecanut"
    assert body["market"] == "Mangalore"
    assert body["days"] == 5
    assert len(body["prices"]) == 5


def test_prices_trend_404(client: TestClient):
    response = client.get("/prices/trend?crop=Arecanut&market=Nowhere")
    assert response.status_code == 404


def test_prices_compare(client: TestClient, session: Session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 410, 390, 430, date(2026, 11, 20))
    _add_price(session, "Arecanut", "Dakshina Kannada", "Puttur", "Karnataka", 400, 380, 420, date(2026, 11, 20))
    _add_price(session, "Arecanut", "Dakshina Kannada", "Bantwal", "Karnataka", 395, 375, 415, date(2026, 11, 20))

    response = client.get("/prices/compare?crop=Arecanut&district=Dakshina Kannada")
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-11-20"
    modals = [p["modal_price"] for p in body["markets"]]
    assert modals == sorted(modals, reverse=True)


def test_prices_compare_404(client: TestClient):
    response = client.get("/prices/compare?crop=Arecanut&district=Unknown")
    assert response.status_code == 404


def test_markets(client: TestClient, session: Session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 410, 390, 430, date(2026, 11, 20))
    _add_price(session, "Coconut", "Dakshina Kannada", "Puttur", "Karnataka", 20, 18, 22, date(2026, 11, 20))

    response = client.get("/markets?district=Dakshina Kannada")
    assert response.status_code == 200
    body = response.json()
    assert body["district"] == "Dakshina Kannada"
    market_names = {m["market"] for m in body["markets"]}
    assert market_names == {"Mangalore", "Puttur"}


def test_markets_404(client: TestClient):
    response = client.get("/markets?district=Unknown")
    assert response.status_code == 404


def test_prices_refresh(client: TestClient, session: Session):
    response = client.post(
        "/prices/refresh?crop=Arecanut&district=Dakshina Kannada"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "source" in body
    assert "inserted" in body
