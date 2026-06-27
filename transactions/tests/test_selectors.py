"""Story 1.5 — month_summary selector tests."""

from datetime import date
from decimal import Decimal

import pytest

from transactions.selectors import month_summary
from transactions.tests.factories import TransactionFactory, UserFactory


@pytest.mark.django_db
def test_empty_user_returns_zero_balance() -> None:
    user = UserFactory()
    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.cash_balance == Decimal("0")
    assert summary.is_empty is True
    assert summary.top_categories == []


@pytest.mark.django_db
def test_cash_balance_is_income_minus_expense() -> None:
    user = UserFactory()
    TransactionFactory(user=user, type="income", amount=Decimal("1000000"), date=date(2026, 6, 5))
    TransactionFactory(user=user, type="expense", amount=Decimal("250000"), date=date(2026, 6, 10))

    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.total_income == Decimal("1000000")
    assert summary.total_expense == Decimal("250000")
    assert summary.cash_balance == Decimal("750000")
    assert summary.is_empty is False


@pytest.mark.django_db
def test_other_months_excluded() -> None:
    user = UserFactory()
    TransactionFactory(user=user, type="expense", amount=Decimal("9999"), date=date(2026, 5, 31))
    TransactionFactory(user=user, type="expense", amount=Decimal("100"), date=date(2026, 6, 15))
    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.total_expense == Decimal("100")
    assert summary.transaction_count == 1


@pytest.mark.django_db
def test_other_currency_excluded() -> None:
    user = UserFactory()
    TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("1000"),
        currency="USD",
        date=date(2026, 6, 5),
    )
    TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("500"),
        currency="UZS",
        date=date(2026, 6, 5),
    )
    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.total_income == Decimal("500")


@pytest.mark.django_db
def test_debt_transactions_excluded_from_cash_balance_story_1_5() -> None:
    """Per epics 1.5 simplification: debt logic lands in Epic 4; cash = income − expense only."""
    user = UserFactory()
    TransactionFactory(user=user, type="income", amount=Decimal("100"), date=date(2026, 6, 1))
    TransactionFactory(user=user, type="expense", amount=Decimal("50"), date=date(2026, 6, 2))
    TransactionFactory(
        user=user,
        type="debt_lent",
        amount=Decimal("999"),
        counterparty="X",
        date=date(2026, 6, 3),
    )
    TransactionFactory(
        user=user,
        type="debt_borrowed",
        amount=Decimal("888"),
        counterparty="Y",
        date=date(2026, 6, 4),
    )
    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.cash_balance == Decimal("50")


@pytest.mark.django_db
def test_top_categories_orders_by_total_desc_and_caps_at_three() -> None:
    # Preset categories are seeded by the data migration; no fixture load needed.
    from categories.models import Category

    user = UserFactory()
    taxi = Category.objects.filter(user__isnull=True, type="expense", slug="taxi").first()
    qahva = Category.objects.filter(user__isnull=True, type="expense", slug="qahva_kafe").first()
    oziq = Category.objects.filter(user__isnull=True, type="expense", slug="oziq_ovqat").first()
    transport = Category.objects.filter(user__isnull=True, type="expense", slug="transport").first()

    TransactionFactory(
        user=user, type="expense", amount=Decimal("400"), category=taxi, date=date(2026, 6, 1)
    )
    TransactionFactory(
        user=user, type="expense", amount=Decimal("300"), category=qahva, date=date(2026, 6, 2)
    )
    TransactionFactory(
        user=user, type="expense", amount=Decimal("200"), category=oziq, date=date(2026, 6, 3)
    )
    TransactionFactory(
        user=user, type="expense", amount=Decimal("100"), category=transport, date=date(2026, 6, 4)
    )

    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert len(summary.top_categories) == 3
    assert [c.slug for c in summary.top_categories] == ["taxi", "qahva_kafe", "oziq_ovqat"]
    assert summary.top_categories[0].total == Decimal("400")
