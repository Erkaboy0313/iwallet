"""CBU.uz daily-rates HTTP client (Story 5.2).

Sync httpx client — called from a management command / cron once per day, so the
extra async ceremony isn't worth it. Returns a normalized dict; the storage
side lives in `currencies.services.store_rates`.

Endpoint shape (cbu.uz Uzbek archive):

    GET https://cbu.uz/uz/arkhiv-kursov-valyut/json/
    -> [
        {"id": 21, "Code": "840", "Ccy": "USD", "Rate": "12345.67", "Date": "25.06.2026", ...},
        {"id": 57, "Code": "643", "Ccy": "RUB", "Rate": "134.56", "Date": "25.06.2026", ...},
        ...
       ]

We intentionally accept either a list of objects (the public payload) or a
single dict keyed by `Ccy` — defensive against minor shape drift.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from currencies.exceptions import CbuUnavailableError

logger = logging.getLogger(__name__)

CBU_ARCHIVE_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
SUPPORTED_FOREIGN = ("USD", "RUB")
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 0.5


def _parse_date(value: str) -> date:
    """Parse CBU's 'DD.MM.YYYY' string into a `date`."""
    return datetime.strptime(value, "%d.%m.%Y").date()


def _parse_rate(value: str | float | int) -> Decimal:
    """Parse a rate value into Decimal; never via float."""
    return Decimal(str(value))


def _normalize_payload(payload: Any) -> list[dict[str, Any]]:
    """Coerce CBU response into a list of currency dicts.

    Accepts:
        - list[dict]               — public API today
        - {Ccy: dict}              — defensive (single-currency endpoint variant)
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return list(payload.values())
    msg = f"Unexpected CBU.uz payload type: {type(payload).__name__}"
    raise CbuUnavailableError(msg)


def _extract_rates(payload: Any) -> dict[str, Any]:
    """Take CBU's payload and return a dict {USD: Decimal, RUB: Decimal, date: date}.

    Logs and skips currencies that fail to parse; raises CbuUnavailableError if
    we couldn't extract any supported currency at all (signals a real outage).
    """
    rows = _normalize_payload(payload)
    rates: dict[str, Decimal] = {}
    payload_date: date | None = None

    for row in rows:
        if not isinstance(row, dict):
            continue
        ccy = row.get("Ccy") or row.get("ccy")
        if ccy not in SUPPORTED_FOREIGN:
            continue
        rate_raw = row.get("Rate") or row.get("rate")
        date_raw = row.get("Date") or row.get("date")
        if rate_raw is None or date_raw is None:
            logger.warning("cbu.uz parse skip currency=%s — missing Rate/Date", ccy)
            continue
        try:
            rates[ccy] = _parse_rate(rate_raw)
        except (InvalidOperation, ValueError) as exc:
            logger.warning("cbu.uz parse skip currency=%s rate=%r — %s", ccy, rate_raw, exc)
            continue
        try:
            payload_date = _parse_date(date_raw)
        except ValueError as exc:
            logger.warning("cbu.uz parse skip currency=%s date=%r — %s", ccy, date_raw, exc)

    if not rates or payload_date is None:
        msg = "CBU.uz returned no parseable supported-currency rows"
        raise CbuUnavailableError(msg)

    return {**rates, "date": payload_date}


def fetch_cbu_rates(
    *,
    url: str = CBU_ARCHIVE_URL,
    client: httpx.Client | None = None,
    max_attempts: int = MAX_ATTEMPTS,
    sleep: Any = time.sleep,
) -> dict[str, Any]:
    """Hit cbu.uz/uz/arkhiv-kursov-valyut/json/ and return parsed rates.

    Retries up to ``max_attempts`` with exponential backoff on network or HTTP
    errors. Raises :class:`CbuUnavailableError` on terminal failure so the
    caller (Celery task / management command) can decide whether to crash or
    fall back to the stored stale rate.
    """
    last_error: Exception | None = None
    owns_client = client is None
    client = client or httpx.Client(timeout=DEFAULT_TIMEOUT)

    try:
        for attempt in range(1, max_attempts + 1):
            try:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                wait = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "cbu.uz fetch attempt=%d failed: %s (sleep=%.2fs)",
                    attempt,
                    exc,
                    wait,
                )
                if attempt < max_attempts:
                    sleep(wait)
                continue
            return _extract_rates(payload)
    finally:
        if owns_client:
            client.close()

    msg = f"CBU.uz unreachable after {max_attempts} attempts"
    raise CbuUnavailableError(msg) from last_error
