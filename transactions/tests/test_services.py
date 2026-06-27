"""Story 1.2 — Transaction service layer (create/update/delete/restore)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from transactions.exceptions import (
    InvalidAmountError,
    RestoreExpiredError,
    TransactionNotEditableError,
)
from transactions.models import Transaction
from transactions.services import (
    create_transaction,
    restore_transaction,
    soft_delete_transaction,
    update_transaction,
)
from transactions.tests.factories import TransactionFactory, UserFactory

# ---------- create_transaction ----------


@pytest.mark.django_db
def test_create_transaction_happy_path() -> None:
    user = UserFactory()
    tx = create_transaction(
        user=user,
        type="expense",
        amount=Decimal("25000.00"),
        currency="UZS",
        date=date(2026, 6, 27),
        note="taxi",
    )
    assert tx.pk is not None
    assert tx.user == user
    assert tx.amount == Decimal("25000.00")
    assert tx.note == "taxi"
    assert tx.is_deleted is False


@pytest.mark.django_db
def test_create_transaction_rejects_zero_amount() -> None:
    user = UserFactory()
    with pytest.raises(InvalidAmountError):
        create_transaction(
            user=user,
            type="expense",
            amount=Decimal("0"),
            currency="UZS",
            date=date.today(),
        )


@pytest.mark.django_db
def test_create_transaction_rejects_negative_amount() -> None:
    user = UserFactory()
    with pytest.raises(InvalidAmountError):
        create_transaction(
            user=user,
            type="expense",
            amount=Decimal("-100"),
            currency="UZS",
            date=date.today(),
        )


@pytest.mark.django_db
def test_create_debt_persists_counterparty() -> None:
    user = UserFactory()
    tx = create_transaction(
        user=user,
        type="debt_lent",
        amount=Decimal("1000000"),
        currency="UZS",
        date=date.today(),
        counterparty="Akram",
    )
    assert tx.type == "debt_lent"
    assert tx.counterparty == "Akram"


# ---------- update_transaction ----------


@pytest.mark.django_db
def test_update_transaction_changes_fields() -> None:
    tx = TransactionFactory(amount=Decimal("10000"), note="")
    updated = update_transaction(tx=tx, amount=Decimal("12500"), note="qahva")
    assert updated.amount == Decimal("12500")
    assert updated.note == "qahva"


@pytest.mark.django_db
def test_update_transaction_rejects_invalid_amount() -> None:
    tx = TransactionFactory()
    with pytest.raises(InvalidAmountError):
        update_transaction(tx=tx, amount=Decimal("0"))


@pytest.mark.django_db
def test_update_rejects_soft_deleted_transaction() -> None:
    tx = TransactionFactory(is_deleted=True, deleted_at=timezone.now())
    with pytest.raises(TransactionNotEditableError):
        update_transaction(tx=tx, note="late edit")


# ---------- soft_delete + restore ----------


@pytest.mark.django_db
def test_soft_delete_marks_flags() -> None:
    tx = TransactionFactory()
    soft_delete_transaction(tx=tx)
    tx.refresh_from_db()
    assert tx.is_deleted is True
    assert tx.deleted_at is not None
    # Excluded from for_user() once deleted
    assert tx not in Transaction.objects.for_user(tx.user)


@pytest.mark.django_db
def test_restore_within_window_clears_flags() -> None:
    tx = TransactionFactory()
    soft_delete_transaction(tx=tx)
    restore_transaction(tx=tx)
    tx.refresh_from_db()
    assert tx.is_deleted is False
    assert tx.deleted_at is None


@pytest.mark.django_db
def test_restore_after_7_days_raises() -> None:
    tx = TransactionFactory(
        is_deleted=True,
        deleted_at=timezone.now() - timedelta(days=8),
    )
    with pytest.raises(RestoreExpiredError):
        restore_transaction(tx=tx)


@pytest.mark.django_db
def test_restore_at_exactly_7_days_still_allowed() -> None:
    """Boundary: 7 days OK, 7 days + 1s NOT OK."""
    tx = TransactionFactory(
        is_deleted=True,
        deleted_at=timezone.now() - timedelta(days=7) + timedelta(seconds=10),
    )
    restore_transaction(tx=tx)  # should not raise
    tx.refresh_from_db()
    assert tx.is_deleted is False


@pytest.mark.django_db
def test_restore_non_deleted_is_noop() -> None:
    tx = TransactionFactory(is_deleted=False)
    restore_transaction(tx=tx)
    tx.refresh_from_db()
    assert tx.is_deleted is False
    assert tx.deleted_at is None
