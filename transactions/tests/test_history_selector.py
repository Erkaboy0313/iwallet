"""Story 1.6 — history_list selector."""

from datetime import date
from decimal import Decimal

import pytest

from transactions.selectors import history_list
from transactions.tests.factories import TransactionFactory, UserFactory


@pytest.mark.django_db
def test_returns_reverse_chronological_by_default() -> None:
    user = UserFactory()
    a = TransactionFactory(user=user, date=date(2026, 6, 1))
    b = TransactionFactory(user=user, date=date(2026, 6, 5))
    c = TransactionFactory(user=user, date=date(2026, 6, 10))

    qs = list(history_list(user))
    assert qs == [c, b, a]


@pytest.mark.django_db
def test_filters_by_type() -> None:
    user = UserFactory()
    income = TransactionFactory(user=user, type="income")
    expense = TransactionFactory(user=user, type="expense")
    debt = TransactionFactory(user=user, type="debt_lent", counterparty="X")

    assert list(history_list(user, type_="income")) == [income]
    assert list(history_list(user, type_="expense")) == [expense]
    assert list(history_list(user, type_="debt_lent")) == [debt]


@pytest.mark.django_db
def test_filters_by_currency() -> None:
    user = UserFactory()
    uzs = TransactionFactory(user=user, currency="UZS", amount=Decimal("100"))
    TransactionFactory(user=user, currency="USD", amount=Decimal("50"))
    assert list(history_list(user, currency="UZS")) == [uzs]


@pytest.mark.django_db
def test_excludes_soft_deleted() -> None:
    user = UserFactory()
    live = TransactionFactory(user=user)
    TransactionFactory(user=user, is_deleted=True)
    assert list(history_list(user)) == [live]


@pytest.mark.django_db
def test_filters_by_date_range_inclusive() -> None:
    user = UserFactory()
    inside = TransactionFactory(user=user, date=date(2026, 6, 5))
    TransactionFactory(user=user, date=date(2026, 5, 31))
    TransactionFactory(user=user, date=date(2026, 6, 11))

    qs = list(history_list(user, start=date(2026, 6, 1), end=date(2026, 6, 10)))
    assert qs == [inside]


@pytest.mark.django_db
def test_owner_isolation() -> None:
    alice = UserFactory(telegram_id=1)
    bob = UserFactory(telegram_id=2)
    a_tx = TransactionFactory(user=alice)
    TransactionFactory(user=bob)
    assert list(history_list(alice)) == [a_tx]
