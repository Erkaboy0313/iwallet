"""Services: upsert + display conversion (Stories 5.2 and 5.4).

`store_rates` is atomic per call; `convert_for_display` is pure — no DB writes,
and it never raises on missing rates (returns a stale=True / rate_date=None
hint so the UI can decide between "show stale banner" and "fall back to raw").
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction as db_transaction
from django.utils import timezone

from currencies.cbu_client import fetch_cbu_rates
from currencies.exceptions import CbuUnavailableError, MissingRateError
from currencies.models import SOURCE_CBU, ExchangeRate
from currencies.selectors import RateLookup, latest_rate

logger = logging.getLogger(__name__)

REFRESH_INTERVAL = timedelta(days=1)
DISPLAY_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class ConversionResult:
    """Outcome of a conversion call — what to show + freshness hints for the UI."""

    amount: Decimal  # Always quantized to 2dp for display.
    from_currency: str
    to_currency: str
    rate_date: date | None  # None when no rate found anywhere.
    is_stale: bool  # True if we fell back to a previous-day rate.
    converted: bool  # False when from == to (identity).


def store_rates(
    *,
    on_date: date,
    rates: dict[str, Decimal],
    source: str = SOURCE_CBU,
) -> list[ExchangeRate]:
    """Upsert one ExchangeRate per (currency, date). Atomic per call.

    Keys other than the three-letter currency codes (e.g., the ``date`` key in
    the CBU client payload) are silently skipped so the caller can pass the
    raw dict through.
    """
    saved: list[ExchangeRate] = []
    with db_transaction.atomic():
        for currency, raw in rates.items():
            if len(currency) != 3 or not currency.isalpha():
                # Skip non-currency keys (e.g., 'date').
                continue
            row, _created = ExchangeRate.objects.update_or_create(
                currency=currency,
                date=on_date,
                defaults={"rate_to_uzs": Decimal(str(raw)), "source": source},
            )
            saved.append(row)
    logger.info("Stored %d ExchangeRate rows for %s", len(saved), on_date)
    return saved


def update_rates_if_stale(*, today: date | None = None) -> bool:
    """Fetch + store CBU.uz rates if today's rates are missing.

    Returns True if a fetch happened (regardless of whether it succeeded —
    the caller logs CbuUnavailableError); False if we already had today's
    rates and skipped the network call. Never raises: the goal of this
    function is "best effort, don't crash the worker".
    """
    today = today or timezone.localdate()
    if ExchangeRate.objects.filter(date=today).exists():
        logger.debug("Rates already present for %s — skipping CBU fetch", today)
        return False
    try:
        payload = fetch_cbu_rates()
    except CbuUnavailableError as exc:
        logger.warning("CBU.uz fetch failed; stale rates will be used: %s", exc)
        return True

    payload_date = payload.pop("date", today)
    rates = {k: v for k, v in payload.items() if isinstance(v, Decimal)}
    if not rates:
        logger.warning("CBU.uz payload had no Decimal rates after parsing")
        return True
    store_rates(on_date=payload_date, rates=rates)
    return True


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(DISPLAY_QUANTUM, rounding=ROUND_HALF_UP)


def convert_for_display(
    amount: Any,
    from_currency: str,
    to_currency: str,
    *,
    as_of_date: date | None = None,
) -> ConversionResult:
    """Convert ``amount`` from ``from_currency`` to ``to_currency``.

    Path: always pivot through UZS. UZS↔X uses the stored rate directly; X↔Y
    multiplies by from_rate and divides by to_rate.

    Returns a :class:`ConversionResult`. Caller checks ``is_stale`` /
    ``rate_date is None`` to decide whether to render a warning. Raises
    :class:`MissingRateError` ONLY when there is no rate at all anywhere for
    the requested currency — that's a "system never bootstrapped" signal, not
    a "stale" signal.
    """
    decimal_amount = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return ConversionResult(
            amount=_quantize(decimal_amount),
            from_currency=from_currency,
            to_currency=to_currency,
            rate_date=as_of_date or timezone.localdate(),
            is_stale=False,
            converted=False,
        )

    from_rate = latest_rate(from_currency, on_or_before=as_of_date)
    to_rate = latest_rate(to_currency, on_or_before=as_of_date)

    if from_rate is None or to_rate is None:
        missing = from_currency if from_rate is None else to_currency
        msg = f"No ExchangeRate available for {missing}"
        raise MissingRateError(msg)

    uzs_value = decimal_amount * from_rate.rate_to_uzs
    converted_value = uzs_value / to_rate.rate_to_uzs

    rate_date = min(from_rate.rate_date, to_rate.rate_date)
    is_stale = from_rate.is_stale or to_rate.is_stale

    return ConversionResult(
        amount=_quantize(converted_value),
        from_currency=from_currency,
        to_currency=to_currency,
        rate_date=rate_date,
        is_stale=is_stale,
        converted=True,
    )


def safe_convert_for_display(
    amount: Any,
    from_currency: str,
    to_currency: str,
    *,
    as_of_date: date | None = None,
) -> ConversionResult | None:
    """Same as ``convert_for_display`` but returns ``None`` instead of raising.

    Used by views/selectors that want the "fall back to raw amounts" path when
    rates aren't bootstrapped yet (first-deploy, fresh DB, etc.).
    """
    try:
        return convert_for_display(
            amount,
            from_currency,
            to_currency,
            as_of_date=as_of_date,
        )
    except MissingRateError as exc:
        logger.info("safe_convert_for_display falling back to raw: %s", exc)
        return None


def _ratelookup_or_identity(currency: str, *, as_of_date: date | None = None) -> RateLookup | None:
    """Sugar used by callers that just need the freshness info for a currency."""
    return latest_rate(currency, on_or_before=as_of_date)
