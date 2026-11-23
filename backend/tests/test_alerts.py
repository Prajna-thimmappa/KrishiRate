"""Alert API and trigger logic tests with mocked Telegram."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from backend.app.models import Alert, Price
from backend.app.services.alert_service import check_and_trigger_alerts


def _add_price(session, crop, district, market, state, modal, mn, mx, d):
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


def _post_alert(client, chat_id, crop, district, target_price, condition="above", market=None):
    params = [
        ("chat_id", chat_id),
        ("crop", crop),
        ("district", district),
        ("target_price", str(target_price)),
        ("condition", condition),
    ]
    if market:
        params.append(("market", market))
    return client.post("/alerts", params=params)


# ---------- CRUD endpoints ----------

def test_create_alert(client):
    response = _post_alert(client, "12345", "Arecanut", "Dakshina Kannada", 420)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    alert = body["alert"]
    assert alert["chat_id"] == "12345"
    assert alert["crop"] == "Arecanut"
    assert alert["district"] == "Dakshina Kannada"
    assert alert["target_price"] == 420
    assert alert["condition"] == "above"
    assert alert["active"] is True


def test_create_alert_below_condition(client):
    response = _post_alert(client, "12345", "Coconut", "Udupi", 20, condition="below")
    assert response.status_code == 201
    assert response.json()["alert"]["condition"] == "below"


def test_create_alert_invalid_condition_422(client):
    response = _post_alert(client, "12345", "Arecanut", "Dakshina Kannada", 420, condition="equals")
    assert response.status_code == 422


def test_create_alert_missing_params_422(client):
    response = client.post("/alerts?chat_id=12345")
    assert response.status_code == 422


def test_list_alerts(client, session):
    _post_alert(client, "chat-1", "Arecanut", "Dakshina Kannada", 420)
    _post_alert(client, "chat-1", "Coconut", "Udupi", 25)
    _post_alert(client, "chat-2", "Arecanut", "Dakshina Kannada", 400)

    response = client.get("/alerts?chat_id=chat-1")
    assert response.status_code == 200
    body = response.json()
    assert body["chat_id"] == "chat-1"
    assert len(body["alerts"]) == 2

    response = client.get("/alerts?chat_id=chat-2")
    assert len(response.json()["alerts"]) == 1

    response = client.get("/alerts?chat_id=none")
    assert response.json()["alerts"] == []


def test_list_alerts_missing_chat_id_422(client):
    response = client.get("/alerts")
    assert response.status_code == 422


def test_delete_alert(client, session):
    create_res = _post_alert(client, "12345", "Arecanut", "Dakshina Kannada", 420)
    alert_id = create_res.json()["alert"]["id"]

    response = client.delete(f"/alerts/{alert_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] == alert_id

    # Gone now.
    response = client.get("/alerts?chat_id=12345")
    assert len(response.json()["alerts"]) == 0


def test_delete_alert_not_found(client):
    response = client.delete("/alerts/99999")
    assert response.status_code == 404


# ---------- Trigger logic (Telegram mocked) ----------

@patch("backend.app.services.alert_service.send_message", return_value=True)
def test_trigger_above(mock_send, session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 450, 430, 470, date(2026, 11, 20))
    session.add(
        Alert(
            chat_id="12345",
            crop="Arecanut",
            district="Dakshina Kannada",
            market="Mangalore",
            target_price=420,
            condition="above",
            active=True,
        )
    )
    session.commit()

    triggered = check_and_trigger_alerts(session)
    assert triggered == 1
    mock_send.assert_called_once()
    # last_triggered_at stamped.
    alert = session.query(Alert).first()
    assert alert.last_triggered_at is not None


@patch("backend.app.services.alert_service.send_message", return_value=True)
def test_trigger_below(mock_send, session):
    _add_price(session, "Coconut", "Udupi", "Kundapura", "Karnataka", 15, 12, 18, date(2026, 11, 20))
    session.add(
        Alert(
            chat_id="12345",
            crop="Coconut",
            district="Udupi",
            market="Kundapura",
            target_price=20,
            condition="below",
            active=True,
        )
    )
    session.commit()

    triggered = check_and_trigger_alerts(session)
    assert triggered == 1
    mock_send.assert_called_once()


@patch("backend.app.services.alert_service.send_message", return_value=True)
def test_no_trigger_when_condition_not_met(mock_send, session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 400, 380, 420, date(2026, 11, 20))
    session.add(
        Alert(
            chat_id="12345",
            crop="Arecanut",
            district="Dakshina Kannada",
            target_price=420,
            condition="above",
            active=True,
        )
    )
    session.commit()

    triggered = check_and_trigger_alerts(session)
    assert triggered == 0
    mock_send.assert_not_called()


@patch("backend.app.services.alert_service.send_message", return_value=True)
def test_24h_cooldown_prevents_retrigger(mock_send, session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 450, 430, 470, date(2026, 11, 20))
    session.add(
        Alert(
            chat_id="12345",
            crop="Arecanut",
            district="Dakshina Kannada",
            target_price=420,
            condition="above",
            active=True,
            last_triggered_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
    )
    session.commit()

    triggered = check_and_trigger_alerts(session)
    assert triggered == 0
    mock_send.assert_not_called()


@patch("backend.app.services.alert_service.send_message", return_value=True)
def test_trigger_after_cooldown_expired(mock_send, session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 450, 430, 470, date(2026, 11, 20))
    session.add(
        Alert(
            chat_id="12345",
            crop="Arecanut",
            district="Dakshina Kannada",
            target_price=420,
            condition="above",
            active=True,
            last_triggered_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
    )
    session.commit()

    triggered = check_and_trigger_alerts(session)
    assert triggered == 1
    mock_send.assert_called_once()


@patch("backend.app.services.alert_service.send_message", return_value=True)
def test_inactive_alert_not_triggered(mock_send, session):
    _add_price(session, "Arecanut", "Dakshina Kannada", "Mangalore", "Karnataka", 450, 430, 470, date(2026, 11, 20))
    session.add(
        Alert(
            chat_id="12345",
            crop="Arecanut",
            district="Dakshina Kannada",
            target_price=420,
            condition="above",
            active=False,
        )
    )
    session.commit()

    triggered = check_and_trigger_alerts(session)
    assert triggered == 0
    mock_send.assert_not_called()
