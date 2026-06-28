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
from django.utils import timezone

from accounts.models import User

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
