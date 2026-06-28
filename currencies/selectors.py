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

    Avoids a circular import by deferring `month_summary` + `convert_for_display`
    until call time.
    """
    # Local imports — `currencies.selectors` is imported by `accounts.models`
    # via `currencies.constants`, but `transactions.selectors` itself imports
    # from `accounts.models`. Going through the function-local import keeps
    # the boot graph clean.
    from currencies.services import safe_convert_for_display
    from transactions.selectors import month_summary

    today = today or timezone.localdate()

    per_currency: list[PerCurrencySummary] = []
    total_income = Decimal("0")
    total_expense = Decimal("0")
    transaction_count = 0
    earliest_rate_date: date | None = None
    any_stale = False
    fully_supported = True

    for ccy in CURRENCY_CODES:
        per = month_summary(user, ccy, today=today)
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
            total_income += per.total_income
            total_expense += per.total_expense
            continue

        income_conv = safe_convert_for_display(
            per.total_income,
            ccy,
            display_currency,
            as_of_date=today,
        )
        expense_conv = safe_convert_for_display(
            per.total_expense,
            ccy,
            display_currency,
            as_of_date=today,
        )
        if income_conv is None or expense_conv is None:
            # No rate at all — flag for the view to fall back to raw.
            fully_supported = False
            continue
        total_income += income_conv.amount
        total_expense += expense_conv.amount

        for conv in (income_conv, expense_conv):
            if conv.rate_date is not None and (
                earliest_rate_date is None or conv.rate_date < earliest_rate_date
            ):
                earliest_rate_date = conv.rate_date
            if conv.is_stale:
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
