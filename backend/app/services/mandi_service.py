"""Mandi price fetcher for KrishiRate.

Tries the Government of India Open Data API (data.gov.in, Agmarknet dataset)
for today's mandi prices. If the API is unavailable or misconfigured, falls
back to the local sample CSV in data/sample_prices.csv so the app still runs.

All price records are normalized to the same shape:
{
    "commodity": str,
    "district": str,
    "market": str,
    "state": str,
    "modal_price": float | None,
    "min_price": float | None,
    "max_price": float | None,
    "arrival_date": str,
}
"""

import csv
import os
from typing import Dict, List, Optional, Tuple

import requests

from ..config import DATA_GOV_API_KEY

# data.gov.in resource endpoint for Agmarknet daily mandi prices.
# Override with DATA_GOV_RESOURCE_ID in .env if your key maps to a different resource.
DATA_GOV_BASE = "https://api.data.gov.in/resource/"
DATA_GOV_RESOURCE_ID = os.getenv(
    "DATA_GOV_RESOURCE_ID", "9ef8426c-d546-49ea-a7cf-19c79e35c7d7"
)

# Path to the fallback sample CSV shipped with the app.
SAMPLE_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "sample_prices.csv",
)

# Last successfully used data source (set by fetch_prices / sync_service).
LAST_SOURCE: Optional[str] = None


def _to_float(value) -> Optional[float]:
    """Convert a value to float, returning None when it is missing or invalid."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_record(row: Dict) -> Dict:
    """Map a raw API/CSV row into the standard price-record shape."""
    return {
        "commodity": str(row.get("commodity", "")).strip(),
        "district": str(row.get("district", "")).strip(),
        "market": str(row.get("market", "")).strip(),
        "state": str(row.get("state", "")).strip(),
        "modal_price": _to_float(row.get("modal_price")),
        "min_price": _to_float(row.get("min_price")),
        "max_price": _to_float(row.get("max_price")),
        "arrival_date": str(row.get("arrival_date", "")).strip(),
    }


def fetch_from_api(commodity: str, district: str, limit: int = 10) -> List[Dict]:
    """Query data.gov.in for mandi prices of one commodity in one district.

    Raises when the API key is missing, the request fails, or the response is
    malformed - callers should catch and fall back to the CSV.
    """
    if not DATA_GOV_API_KEY:
        raise RuntimeError("DATA_GOV_API_KEY is not set in .env")

    url = f"{DATA_GOV_BASE}{DATA_GOV_RESOURCE_ID}"
    params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "limit": str(limit),
        "filters[commodity]": commodity,
        "filters[district]": district,
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    records = payload.get("records", [])
    return [_normalize_record(record) for record in records]


def load_from_csv(commodity: str, district: str) -> List[Dict]:
    """Load matching price rows from the local sample CSV fallback."""
    results: List[Dict] = []
    if not os.path.exists(SAMPLE_CSV):
        return results

    with open(SAMPLE_CSV, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if (
                row.get("commodity", "").strip().lower() == commodity.lower()
                and row.get("district", "").strip().lower() == district.lower()
            ):
                results.append(_normalize_record(row))
    return results


def fetch_prices(
    commodity: str = "Arecanut", district: str = "Dakshina Kannada"
) -> Tuple[List[Dict], str]:
    """Fetch mandi prices.

    Tries the data.gov.in API first. On any failure (no key, network error,
    HTTP error, empty result) it falls back to the sample CSV.

    Returns a tuple of (price_records, source_label).
    """
    global LAST_SOURCE
    try:
        prices = fetch_from_api(commodity, district)
        if prices:
            LAST_SOURCE = "data.gov.in API"
            return prices, "data.gov.in API"
    except Exception as exc:  # noqa: BLE001 - any failure triggers the CSV fallback
        print(f"[warn] data.gov.in API unavailable ({exc}); falling back to sample CSV")

    prices = load_from_csv(commodity, district)
    LAST_SOURCE = "sample CSV (fallback)" if prices else None
    return prices, "sample CSV (fallback)"


def print_table(
    prices: List[Dict], source: str, commodity: str, district: str
) -> None:
    """Print the price records as a clean terminal table."""
    print(f"\nKrishiRate - {commodity} prices in {district}")
    print(f"Source: {source}")

    if not prices:
        print("No price data available.\n")
        return

    header = f"{'Market':<22} {'Modal':>8} {'Min':>8} {'Max':>8} {'Date':<12}"
    print(header)
    print("-" * len(header))
    for record in prices:
        modal = f"{record['modal_price']:.0f}" if record["modal_price"] is not None else "N/A"
        minimum = f"{record['min_price']:.0f}" if record["min_price"] is not None else "N/A"
        maximum = f"{record['max_price']:.0f}" if record["max_price"] is not None else "N/A"
        print(
            f"{record['market']:<22} {modal:>8} {minimum:>8} {maximum:>8} "
            f"{record['arrival_date']:<12}"
        )
    print()


def main() -> None:
    """CLI entry point: fetch and print prices for one crop and one district."""
    commodity = os.getenv("KRISHI_COMMODITY", "Arecanut")
    district = os.getenv("KRISHI_DISTRICT", "Dakshina Kannada")
    prices, source = fetch_prices(commodity, district)
    print_table(prices, source, commodity, district)


if __name__ == "__main__":
    main()
