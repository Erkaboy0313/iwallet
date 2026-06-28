"""Read-side selectors for currency rates (Epic 5).

Pure DB reads — no fetch, no mutation. The conversion helper in
`currencies.services` composes these.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.utils import timezone

from currencies.models import ExchangeRate


@dataclass(frozen=True)
class RateLookup:
    """The rate we found + freshness info for the UI banner."""

    rate_to_uzs: Decimal
    rate_date: date
    is_stale: bool  # True if `rate_date` < requested as_of_date


def latest_rate(currency: str, *, on_or_before: date | None = None) -> RateLookup | None:
    """Return the most recent ExchangeRate for ``currency`` no later than ``on_or_before``.

    ``on_or_before`` defaults to today. Returns ``None`` if no rate exists at all.
    """
    if currency == "UZS":
        # Identity rate — surfaces as Decimal('1') with today's date, never stale.
        ref = on_or_before or timezone.localdate()
        return RateLookup(rate_to_uzs=Decimal("1"), rate_date=ref, is_stale=False)

    target_date = on_or_before or timezone.localdate()
    row = (
        ExchangeRate.objects.filter(currency=currency, date__lte=target_date)
        .order_by("-date")
        .first()
    )
    if row is None:
        return None
    return RateLookup(
        rate_to_uzs=row.rate_to_uzs,
        rate_date=row.date,
        is_stale=row.date < target_date,
    )


def current_rates_stale_days(*, today: date | None = None) -> int:
    """Days since the most recent ExchangeRate across all foreign currencies.

    Returns 0 if today's rate is present, large positive number if stale,
    -1 if no rates exist at all (caller treats as "fall back to raw amounts").
    """
    today = today or timezone.localdate()
    latest = ExchangeRate.objects.order_by("-date").first()
    if latest is None:
        return -1
    return (today - latest.date).days
