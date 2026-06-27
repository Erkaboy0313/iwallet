"""Story 1.1 — Transaction model + manager + constraints."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction as db_transaction

from transactions.models import Transaction
from transactions.tests.factories import TransactionFactory, UserFactory

# ---------- Field & constraint sanity ----------


@pytest.mark.django_db
def test_transaction_amount_must_be_positive() -> None:
    """CheckConstraint amount > 0 rejects zero and negative."""
    user = UserFactory()
    for bad in (Decimal("0"), Decimal("-1.00")):
        with db_transaction.atomic(), pytest.raises(IntegrityError):
            Transaction.objects.create(
                user=user,
                type="expense",
                amount=bad,
                currency="UZS",
                date=date.today(),
            )


def test_transaction_type_choices_enforced() -> None:
    """Only the 4 known types are exposed via the model's choice list."""
    valid_types = {"income", "expense", "debt_lent", "debt_borrowed"}
    found = {value for value, _label in Transaction._meta.get_field("type").choices}
    assert valid_types == found


@pytest.mark.django_db
def test_transaction_default_is_not_deleted() -> None:
    tx = TransactionFactory()
    assert tx.is_deleted is False
    assert tx.deleted_at is None


# ---------- TransactionManager.for_user ----------


@pytest.mark.django_db
def test_for_user_filters_by_owner() -> None:
    alice = UserFactory(telegram_id=1)
    bob = UserFactory(telegram_id=2)
    TransactionFactory(user=alice)
    TransactionFactory(user=alice)
    TransactionFactory(user=bob)

    assert Transaction.objects.for_user(alice).count() == 2
    assert Transaction.objects.for_user(bob).count() == 1


@pytest.mark.django_db
def test_for_user_excludes_soft_deleted() -> None:
    user = UserFactory()
    kept = TransactionFactory(user=user)
    deleted = TransactionFactory(user=user, is_deleted=True)

    qs = Transaction.objects.for_user(user)
    assert kept in qs
    assert deleted not in qs


# ---------- TransactionManager.in_period ----------


@pytest.mark.django_db
def test_in_period_inclusive_bounds() -> None:
    user = UserFactory()
    on_start = TransactionFactory(user=user, date=date(2026, 6, 1))
    middle = TransactionFactory(user=user, date=date(2026, 6, 15))
    on_end = TransactionFactory(user=user, date=date(2026, 6, 30))
    before = TransactionFactory(user=user, date=date(2026, 5, 31))
    after = TransactionFactory(user=user, date=date(2026, 7, 1))

    qs = Transaction.objects.for_user(user).in_period(start=date(2026, 6, 1), end=date(2026, 6, 30))
    assert set(qs) == {on_start, middle, on_end}
    assert before not in qs
    assert after not in qs


# ---------- TransactionManager.by_type ----------


@pytest.mark.django_db
def test_by_type_filters_correctly() -> None:
    user = UserFactory()
    income = TransactionFactory(user=user, type="income")
    expense = TransactionFactory(user=user, type="expense")
    debt = TransactionFactory(user=user, type="debt_borrowed")

    assert list(Transaction.objects.for_user(user).by_type("income")) == [income]
    assert list(Transaction.objects.for_user(user).by_type("expense")) == [expense]
    assert list(Transaction.objects.for_user(user).by_type("debt_borrowed")) == [debt]


# ---------- Indexes ----------


@pytest.mark.django_db
def test_indexes_exist_on_user_date_and_user_type_date() -> None:
    """Required indexes ship in migration (verified by introspecting Meta.indexes)."""
    index_fields = {tuple(idx.fields) for idx in Transaction._meta.indexes}
    assert ("user", "date") in index_fields
    assert ("user", "type", "date") in index_fields
    assert ("user", "is_deleted") in index_fields


# ---------- __str__ + ordering ----------


@pytest.mark.django_db
def test_default_ordering_is_reverse_chronological() -> None:
    """Latest-first ordering supports History list (FR59) out of the box."""
    user = UserFactory()
    older = TransactionFactory(user=user, date=date.today() - timedelta(days=3))
    newer = TransactionFactory(user=user, date=date.today())
    qs = list(Transaction.objects.for_user(user))
    assert qs[0] == newer
    assert qs[-1] == older
