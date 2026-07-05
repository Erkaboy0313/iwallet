"""Write-side business logic for debts (Story 4.1).

Per project-context: services own invariants, views only orchestrate. All
writes are atomic; raises domain exceptions (never bare Exception).

State transitions are logged at INFO so we can audit the lifecycle in
production without parsing DB diffs.
"""

from __future__ import annotations

import logging
from datetime import date as _date_type
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from transactions.models import Transaction, TransactionType

from .exceptions import (
    CurrencyMismatchError,
    DebtAlreadyClosedError,
    InvalidDebtAmountError,
    RepaymentExceedsRemainingError,
)
from .models import Debt, DebtDirection, DebtRepayment, DebtState
from .state_machine import can_apply_repayment, can_cancel, next_state_after_repayment

logger = logging.getLogger(__name__)


def _validate_amount(amount: Decimal) -> None:
    if amount is None or amount <= Decimal("0"):
        raise InvalidDebtAmountError("Summa musbat bo'lishi kerak.")


@db_transaction.atomic
def create_debt(
    *,
    user: User,
    direction: str,
    counterparty: str,
    amount: Decimal,
    currency: str = "UZS",
    expected_return_date: _date_type | None = None,
    note: str = "",
) -> Debt:
    """Create an open debt. `amount` is both `original_amount` and `remaining_amount`."""
    _validate_amount(amount)
    if direction not in {DebtDirection.LENT.value, DebtDirection.BORROWED.value}:
        raise InvalidDebtAmountError(f"Yo'nalish noto'g'ri: {direction!r}.")
    if not (counterparty or "").strip():
        raise InvalidDebtAmountError("Kim bilan ekanini yozing.")

    debt = Debt.objects.create(
        user=user,
        direction=direction,
        counterparty=counterparty.strip(),
        original_amount=amount,
        remaining_amount=amount,
        currency=currency,
        expected_return_date=expected_return_date,
        state=DebtState.OPEN.value,
        note=note,
    )
    logger.info(
        "debt.created id=%s user=%s direction=%s amount=%s %s",
        debt.id,
        user.telegram_id,
        direction,
        amount,
        currency,
    )
    # TODO(Epic 9 Story 9.3): if expected_return_date is set, the daily Beat
    # task `queue_debt_due_reminders` will pick this up — no inline push here.
    return debt


@db_transaction.atomic
def apply_repayment(
    *,
    debt: Debt,
    amount: Decimal,
    currency: str | None = None,
    repaid_at=None,
    note: str = "",
) -> tuple[Debt, DebtRepayment]:
    """Record a (possibly partial) repayment, advancing the debt's state.

    Returns the refreshed Debt + the new DebtRepayment row.

    Raises:
        DebtAlreadyClosedError — debt is closed or cancelled.
        CurrencyMismatchError — currency arg given and ≠ debt currency.
        InvalidDebtAmountError — amount is not strictly positive.
        RepaymentExceedsRemainingError — amount > remaining_amount.
    """
    _validate_amount(amount)

    # Re-fetch with row lock so two concurrent repayments don't both pass the
    # remaining-amount check (project-context concurrency rule).
    debt = Debt.objects.select_for_update().get(pk=debt.pk)

    if not can_apply_repayment(debt):
        raise DebtAlreadyClosedError("Bu qarz allaqachon yopilgan yoki bekor qilingan.")

    if currency is not None and currency != debt.currency:
        # v1 limitation per project-context — cross-currency repayment is rejected.
        raise CurrencyMismatchError(
            f"Valyutalar mos kelmaydi: qarz {debt.currency}, qaytarish {currency}."
        )

    if amount > debt.remaining_amount:
        raise RepaymentExceedsRemainingError(
            f"Qoldiqdan ko'p miqdor kiritildi (qoldiq: {debt.remaining_amount} {debt.currency})."
        )

    when = repaid_at or timezone.now()
    repayment = DebtRepayment.objects.create(
        debt=debt,
        amount=amount,
        repaid_at=when,
        note=note,
    )

    previous_state = debt.state
    debt.remaining_amount = debt.remaining_amount - amount
    debt.state = next_state_after_repayment(debt, Decimal("0"))  # remaining already decremented
    debt.save(update_fields=["remaining_amount", "state", "updated_at"])

    logger.info(
        "debt.repaid id=%s amount=%s remaining=%s state=%s->%s",
        debt.id,
        amount,
        debt.remaining_amount,
        previous_state,
        debt.state,
    )
    return debt, repayment


@db_transaction.atomic
def cancel_debt(*, debt: Debt, reason: str = "") -> Debt:
    """Forgive / void a debt. Closed-or-cancelled debts raise.

    `reason` is a short tag (e.g. ``"forgiven"``) we persist alongside the
    state change so the timeline view can show *why* a debt disappeared.
    """
    debt = Debt.objects.select_for_update().get(pk=debt.pk)

    if not can_cancel(debt):
        raise DebtAlreadyClosedError("Bu qarz allaqachon yopilgan yoki bekor qilingan.")

    previous_state = debt.state
    debt.state = DebtState.CANCELLED.value
    debt.cancelled_reason = (reason or "").strip()[:64]
    debt.save(update_fields=["state", "cancelled_reason", "updated_at"])

    logger.info(
        "debt.cancelled id=%s reason=%r state=%s->%s",
        debt.id,
        debt.cancelled_reason,
        previous_state,
        debt.state,
    )
    return debt


# --- Sprint v0.8.1 — partial repayment for Transaction-based debts ---------
#
# The Qarzlar screen (debts/views.py) operates on Transaction rows directly,
# not on the Debt aggregate above. This service records a partial repayment
# as its own Transaction (debt_repaid_by_me / debt_repaid_to_me) and
# opportunistically flips settled_at on the original debt row when the
# running counterparty balance in that direction is fully covered.
#
# Accounting approximation (per story spec): remaining balance is tracked
# per (user, counterparty, currency, direction) — NOT per specific debt row.
# Real users think about totals ("Karim menga 200k qaytardi"), not which of
# their three loans to Karim it covered. This trades granularity for a UX
# that matches how the debt is discussed in Uzbek and keeps the model
# simple. Trade-off: if a user records overlapping debts to the same person
# in the same currency, the "which one got closed" mapping is fuzzy but the
# hero math (see all_time_totals) stays correct because it operates on the
# same aggregation.


REPAYMENT_TYPE_FOR_ORIGINAL: dict[str, str] = {
    TransactionType.DEBT_BORROWED.value: TransactionType.DEBT_REPAID_BY_ME.value,
    TransactionType.DEBT_LENT.value: TransactionType.DEBT_REPAID_TO_ME.value,
}


def _remaining_by_counterparty(
    *,
    user: User,
    counterparty: str,
    currency: str,
    original_type: str,
) -> Decimal:
    """Aggregate remaining balance across all debts to this counterparty.

    Sum of open (non-settled, non-deleted) debt rows in ``original_type``
    minus the sum of repayments already logged in the opposite direction.
    Cross-currency debts are kept separate.
    """
    original_sum = Transaction.objects.for_user(user).filter(
        type=original_type,
        counterparty=counterparty,
        currency=currency,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    repaid_sum = Transaction.objects.for_user(user).filter(
        type=REPAYMENT_TYPE_FOR_ORIGINAL[original_type],
        counterparty=counterparty,
        currency=currency,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return original_sum - repaid_sum


@db_transaction.atomic
def record_partial_repayment(
    *,
    user: User,
    original_tx: Transaction,
    amount: Decimal,
    when: _date_type | None = None,
) -> Transaction:
    """Log a partial (or full) repayment against a Transaction-based debt.

    Accounting approximation: we validate ``amount`` against the aggregate
    (user, counterparty, currency, direction) balance — NOT against the
    specific ``original_tx``. This mirrors how users talk about debts
    ("Karim menga 200k qaytardi") and matches the aggregate hero math in
    transactions.selectors.all_time_totals. Trade-off: if the user has
    multiple open debts to the same counterparty in the same currency, a
    repayment reduces the *group* balance; ``original_tx.settled_at`` gets
    flipped only when the group is fully covered.

    Raises:
        InvalidDebtAmountError — non-positive amount, wrong tx type, or
            already-settled/deleted source.
        RepaymentExceedsRemainingError — amount > aggregate remaining
            balance for this (user, counterparty, currency, direction).
    """
    if amount is None or amount <= Decimal("0"):
        raise InvalidDebtAmountError("Summa musbat bo'lishi kerak.")

    if original_tx.type not in REPAYMENT_TYPE_FOR_ORIGINAL:
        raise InvalidDebtAmountError("Faqat qarz tranzaksiyasini qaytarish mumkin.")
    if original_tx.is_deleted:
        raise InvalidDebtAmountError("Bu tranzaksiya o'chirilgan.")

    remaining = _remaining_by_counterparty(
        user=user,
        counterparty=original_tx.counterparty,
        currency=original_tx.currency,
        original_type=original_tx.type,
    )
    if remaining <= Decimal("0"):
        raise RepaymentExceedsRemainingError("Qoldiq yo'q — qarz allaqachon yopilgan.")
    if amount > remaining:
        raise RepaymentExceedsRemainingError(
            f"Qoldiqdan ko'p miqdor kiritildi (qoldiq: {remaining} {original_tx.currency})."
        )

    repayment_type = REPAYMENT_TYPE_FOR_ORIGINAL[original_tx.type]
    label = "Qarz qaytardim" if repayment_type == "debt_repaid_by_me" else "Qarz qaytarib olindi"
    note = f"{label} · {original_tx.counterparty}" if original_tx.counterparty else label

    repayment = Transaction.objects.create(
        user=user,
        type=repayment_type,
        amount=amount,
        currency=original_tx.currency,
        date=when or timezone.localdate(),
        counterparty=original_tx.counterparty,
        note=note,
    )

    # If the aggregate counterparty balance is now fully covered, mark the
    # original row settled so the Qarzlar list drops it out of "Ochiq".
    new_remaining = remaining - amount
    if new_remaining <= Decimal("0") and original_tx.settled_at is None:
        original_tx.settled_at = timezone.now()
        original_tx.save(update_fields=["settled_at", "updated_at"])

    logger.info(
        "debt.partial_repayment tx=%s amount=%s remaining=%s->%s counterparty=%r",
        original_tx.id,
        amount,
        remaining,
        new_remaining,
        original_tx.counterparty,
    )
    return repayment
