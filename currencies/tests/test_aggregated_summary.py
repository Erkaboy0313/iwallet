"""Story 5.5 — aggregated_month_summary selector tests."""

from datetime import date
from decimal import Decimal

import pytest

from currencies.models import ExchangeRate
from currencies.selectors import aggregated_month_summary
from transactions.tests.factories import TransactionFactory, UserFactory


@pytest.mark.django_db
def test_empty_user_returns_zeros() -> None:
    user = UserFactory()
    agg = aggregated_month_summary(user, "UZS", today=date(2026, 6, 15))
    assert agg.cash_balance == Decimal("0")
    assert agg.transaction_count == 0
    assert agg.is_fully_supported is True
    assert agg.per_currency == []


@pytest.mark.django_db
def test_single_currency_path_is_identity() -> None:
    user = UserFactory()
    TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("1000000"),
        currency="UZS",
        date=date(2026, 6, 5),
    )
    agg = aggregated_month_summary(user, "UZS", today=date(2026, 6, 15))
    assert agg.cash_balance == Decimal("1000000")
    assert agg.is_fully_supported is True
    # Single per-currency row.
    assert [r.currency for r in agg.per_currency] == ["UZS"]


@pytest.mark.django_db
def test_mixed_currencies_aggregate_into_uzs_using_rates() -> None:
    user = UserFactory()
    today = date(2026, 6, 15)
    ExchangeRate.objects.create(currency="USD", rate_to_uzs=Decimal("12500.00"), date=today)
    ExchangeRate.objects.create(currency="RUB", rate_to_uzs=Decimal("125.00"), date=today)
    TransactionFactory(
        user=user, type="income", amount=Decimal("1000000"), currency="UZS", date=date(2026, 6, 5)
    )
    TransactionFactory(
        user=user, type="income", amount=Decimal("100"), currency="USD", date=date(2026, 6, 6)
    )
    TransactionFactory(
        user=user, type="expense", amount=Decimal("10000"), currency="RUB", date=date(2026, 6, 7)
    )

    agg = aggregated_month_summary(user, "UZS", today=today)
    # 1_000_000 + 100*12500 - 10000*125 = 1_000_000 + 1_250_000 - 1_250_000 = 1_000_000
    assert agg.cash_balance == Decimal("1000000.00")
    assert agg.total_income == Decimal("2250000.00")
    assert agg.total_expense == Decimal("1250000.00")
    assert agg.is_fully_supported is True
    assert agg.is_stale is False
    assert {r.currency for r in agg.per_currency} == {"UZS", "USD", "RUB"}


@pytest.mark.django_db
def test_missing_rate_marks_not_fully_supported() -> None:
    user = UserFactory()
    today = date(2026, 6, 15)
    # No rates seeded — USD income can't be converted to UZS.
    TransactionFactory(
        user=user, type="income", amount=Decimal("100"), currency="USD", date=date(2026, 6, 5)
    )
    agg = aggregated_month_summary(user, "UZS", today=today)
    assert agg.is_fully_supported is False


@pytest.mark.django_db
def test_stale_rate_propagates_through_aggregate() -> None:
    user = UserFactory()
    today = date(2026, 6, 15)
    ExchangeRate.objects.create(
        currency="USD",
        rate_to_uzs=Decimal("12500.00"),
        date=date(2026, 6, 12),  # 3 days stale
    )
    TransactionFactory(
        user=user, type="income", amount=Decimal("100"), currency="USD", date=date(2026, 6, 5)
    )
    agg = aggregated_month_summary(user, "UZS", today=today)
    assert agg.is_stale is True
    assert agg.rate_date == date(2026, 6, 12)
