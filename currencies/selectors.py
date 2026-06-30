"""Read-side selectors for currency rates (Epic 5).

Pure DB reads — no fetch, no mutation. The conversion helper in
`currencies.services` composes these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.utils import timezone

from accounts.models import User
from currencies.constants import CURRENCY_CODES
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


@dataclass(frozen=True)
class PerCurrencySummary:
    """One row in the per-currency BalanceHero — total income/expense/balance."""

    currency: str
    cash_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    transaction_count: int


@dataclass(frozen=True)
class AggregatedMonthSummary:
    """All transactions for the user collapsed into one display currency.

    Drives the BalanceHero when `User.show_converted` is True (or the user
    has toggled the switcher). When `is_fully_supported` is False, the view
    should fall back to per-currency rendering.
    """

    display_currency: str
    cash_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    transaction_count: int
    per_currency: list[PerCurrencySummary] = field(default_factory=list)
    rate_date: date | None = None
    is_stale: bool = False
    # False when any per-currency total couldn't be converted (no rate at all).
    is_fully_supported: bool = True


def aggregated_month_summary(
    user: User,
    display_currency: str,
    *,
    today: date | None = None,
) -> AggregatedMonthSummary:
    """Sum a user's month across all currencies into ``display_currency``.

    Thin wrapper kept for backwards compatibility; new code should call
    `compute_home_aggregates` and pull out what it needs.
    """
    bundle = compute_home_aggregates(user, today=today)
    return bundle.aggregates[display_currency]


@dataclass(frozen=True)
class HomeAggregatesBundle:
    """All the per-currency totals the home view needs, computed in one pass."""

    summaries: dict  # source_currency → transactions.selectors.MonthSummary
    aggregates: dict  # display_currency → AggregatedMonthSummary


def compute_home_aggregates(
    user: User,
    *,
    today: date | None = None,
) -> HomeAggregatesBundle:
    """Compute everything the home page's currency block needs in one pass.

    Previously the home view called `month_summary` once for the source
    currency and then `aggregated_month_summary` three times for the switcher
    — each of those internally re-ran `month_summary` for every currency
    plus two `latest_rate` lookups per foreign pair. That was roughly
    63 queries for the hero alone. This function pulls each `month_summary`
    once per currency (3 queries) plus each `latest_rate` once (3 queries)
    and composes everything from those caches.
    """
    from currencies.services import _quantize
    from transactions.selectors import month_summary

    today = today or timezone.localdate()

    summaries = {ccy: month_summary(user, ccy, today=today) for ccy in CURRENCY_CODES}
    rate_cache = {ccy: latest_rate(ccy, on_or_before=today) for ccy in CURRENCY_CODES}

    aggregates: dict[str, AggregatedMonthSummary] = {}
    for display_ccy in CURRENCY_CODES:
        aggregates[display_ccy] = _build_aggregate(
            display_currency=display_ccy,
            summaries=summaries,
            rate_cache=rate_cache,
            today=today,
            quantize=_quantize,
        )
    return HomeAggregatesBundle(summaries=summaries, aggregates=aggregates)


def compute_all_currency_aggregates(
    user: User,
    *,
    today: date | None = None,
) -> dict[str, AggregatedMonthSummary]:
    """Back-compat alias — returns just the aggregates map."""
    return compute_home_aggregates(user, today=today).aggregates


def _build_aggregate(
    *,
    display_currency: str,
    summaries: dict,
    rate_cache: dict,
    today: date,  # noqa: ARG001
    quantize,
) -> AggregatedMonthSummary:
    per_currency: list[PerCurrencySummary] = []
    total_income = Decimal("0")
    total_expense = Decimal("0")
    transaction_count = 0
    earliest_rate_date: date | None = None
    any_stale = False
    fully_supported = True

    display_rate = rate_cache.get(display_currency)
    for ccy in CURRENCY_CODES:
        per = summaries[ccy]
        if per.transaction_count == 0:
            continue
        per_currency.append(
            PerCurrencySummary(
                currency=ccy,
                cash_balance=per.cash_balance,
                total_income=per.total_income,
                total_expense=per.total_expense,
                transaction_count=per.transaction_count,
            ),
        )
        transaction_count += per.transaction_count

        if ccy == display_currency:
            total_income += per.inflow_total
            total_expense += per.outflow_total
            continue

        from_rate = rate_cache.get(ccy)
        if from_rate is None or display_rate is None:
            fully_supported = False
            continue

        inflow_converted = quantize(
            per.inflow_total * from_rate.rate_to_uzs / display_rate.rate_to_uzs,
        )
        outflow_converted = quantize(
            per.outflow_total * from_rate.rate_to_uzs / display_rate.rate_to_uzs,
        )
        total_income += inflow_converted
        total_expense += outflow_converted

        for rate in (from_rate, display_rate):
            if earliest_rate_date is None or rate.rate_date < earliest_rate_date:
                earliest_rate_date = rate.rate_date
            if rate.is_stale:
                any_stale = True

    return AggregatedMonthSummary(
        display_currency=display_currency,
        cash_balance=total_income - total_expense,
        total_income=total_income,
        total_expense=total_expense,
        transaction_count=transaction_count,
        per_currency=per_currency,
        rate_date=earliest_rate_date,
        is_stale=any_stale,
        is_fully_supported=fully_supported,
    )
