"""Write-side business logic for transactions (Story 1.2).

Per project-context: services own invariants, views only orchestrate. All writes
are atomic; raises domain exceptions (never bare Exception).
"""

from datetime import date as _date_type, timedelta
from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone

from accounts.models import User

from .exceptions import (
    InvalidAmountError,
    RestoreExpiredError,
    TransactionNotEditableError,
)
from .models import Transaction

# FR8: soft-deleted transactions can be restored for this long.
SOFT_DELETE_RESTORE_WINDOW = timedelta(days=7)


def _validate_amount(amount: Decimal) -> None:
    if amount is None or amount <= 0:
        raise InvalidAmountError("Summa musbat bo'lishi kerak.")


@db_transaction.atomic
def create_transaction(
    *,
    user: User,
    type: str,  # noqa: A002 — matches the model field name
    amount: Decimal,
    currency: str,
    date: _date_type,
    category=None,
    counterparty: str = "",
    note: str = "",
) -> Transaction:
    """Create a transaction with positive-amount enforcement.

    Debt-type entries (debt_lent / debt_borrowed) live as plain Transactions
    too — the Qarzlar tab is just a filter on this table. No separate Debt
    model.
    """
    _validate_amount(amount)
    return Transaction.objects.create(
        user=user,
        type=type,
        amount=amount,
        currency=currency,
        date=date,
        category=category,
        counterparty=counterparty,
        note=note,
    )


@db_transaction.atomic
def update_transaction(*, tx: Transaction, **fields) -> Transaction:
    """Mutate a live transaction. Soft-deleted rows are immutable until restored."""
    if tx.is_deleted:
        raise TransactionNotEditableError("Tranzaksiya o'chirilgan. Avval qaytaring.")
    if "amount" in fields:
        _validate_amount(fields["amount"])
    for field, value in fields.items():
        setattr(tx, field, value)
    tx.save(update_fields=[*fields.keys(), "updated_at"])
    return tx


@db_transaction.atomic
def soft_delete_transaction(*, tx: Transaction) -> Transaction:
    """Mark deleted + stamp deleted_at. for_user() will hide it from now on."""
    if tx.is_deleted:
        return tx
    tx.is_deleted = True
    tx.deleted_at = timezone.now()
    tx.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    return tx


@db_transaction.atomic
def settle_debt_transaction(*, tx: Transaction) -> tuple[Transaction, Transaction]:
    """Mark a debt-type Transaction as settled + spawn the counter cash row.

    debt_lent (I lent money, someone paid me back) -> spawns an `income`.
    debt_borrowed (I borrowed money, I paid them back) -> spawns an `expense`.

    The new cash transaction carries an auto-note tying it back to the
    counterparty so it reads cleanly in History. Returns (original_tx,
    counter_tx).
    """
    if tx.type not in ("debt_lent", "debt_borrowed"):
        raise InvalidAmountError("Faqat qarz tranzaksiyasini yopish mumkin.")
    if tx.settled_at is not None:
        raise TransactionNotEditableError("Bu qarz allaqachon yopilgan.")
    if tx.is_deleted:
        raise TransactionNotEditableError("Tranzaksiya o'chirilgan.")

    if tx.type == "debt_lent":
        counter_type = "income"
        counter_note = "Qarz qaytarib oldim"
    else:
        counter_type = "expense"
        counter_note = "Qarz qaytarib berdim"
    if tx.counterparty:
        counter_note = f"{counter_note} · {tx.counterparty}"

    tx.settled_at = timezone.now()
    tx.save(update_fields=["settled_at", "updated_at"])

    counter = Transaction.objects.create(
        user=tx.user,
        type=counter_type,
        amount=tx.amount,
        currency=tx.currency,
        date=timezone.localdate(),
        counterparty=tx.counterparty,
        note=counter_note,
    )
    return tx, counter


@db_transaction.atomic
def restore_transaction(*, tx: Transaction) -> Transaction:
    """Bring a soft-deleted transaction back if still inside the FR8 window."""
    if not tx.is_deleted:
        return tx
    # Defensive on deleted_at=None — shouldn't happen, but treat as eligible if it does.
    elapsed = timedelta(0) if tx.deleted_at is None else timezone.now() - tx.deleted_at
    if elapsed > SOFT_DELETE_RESTORE_WINDOW:
        raise RestoreExpiredError("Tiklash muddati tugadi (7 kun). Yangi tranzaksiya yarating.")
    tx.is_deleted = False
    tx.deleted_at = None
    tx.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    return tx
