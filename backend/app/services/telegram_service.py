"""Telegram price alerts for KrishiRate.

Sends price alert messages to a configured Telegram chat using the Bot API.
Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the environment (.env).
"""

import requests

from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(text: str) -> bool:
    """Send a text message to the configured Telegram chat.

    Returns True when the message was sent successfully, False otherwise
    (missing credentials, network error, or API error).
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[warn] Telegram credentials not configured; alert not sent")
        return False

    url = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN)
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001 - report and degrade gracefully
        print(f"[warn] Telegram send failed: {exc}")
        return False


def format_alert(crop: str, district: str, market: str, price: dict) -> str:
    """Build a human-readable alert message from a price record."""
    date = price.get("date") or "today"
    modal = price.get("modal_price")
    minimum = price.get("min_price")
    maximum = price.get("max_price")
    fmt = lambda v: "N/A" if v is None else f"\u20B9{v}"
    return (
        f"<b>KrishiRate Price Alert</b>\n"
        f"<b>Crop:</b> {crop}\n"
        f"<b>District:</b> {district}\n"
        f"<b>Market:</b> {market}\n"
        f"<b>Date:</b> {date}\n"
        f"Modal: {fmt(modal)} | Min: {fmt(minimum)} | Max: {fmt(maximum)} /quintal"
    )
