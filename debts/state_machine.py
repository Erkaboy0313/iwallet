"""Explicit Debt state machine (Story 4.1).

Encodes the legal transitions documented in `docs/epics.md::Epic 4 Story 4.1`:

    open → partial         via apply_repayment(amount < remaining)
    open → closed          via apply_repayment(amount == remaining)
    partial → partial      via additional repayment (sum < original)
    partial → closed       via repayment summing to original
    * → cancelled          via cancel_debt(reason)

Closed and cancelled are terminal: no further repayments, no resurrection. The
transitions live here (not on the model) so the test suite and the services
share one source of truth and we can extend with new states (e.g. "disputed")
without touching the model.
"""

from __future__ import annotations

from decimal import Decimal

from .models import Debt, DebtState


def next_state_after_repayment(debt: Debt, repayment_amount: Decimal) -> str:
    """Return the state the debt should transition into after applying repayment.

    Assumes invariants already checked by the service layer (positive amount,
    same currency, not already closed/cancelled, amount ≤ remaining). The state
    machine itself only decides *which* legal state we land in.
    """
    new_remaining = debt.remaining_amount - repayment_amount
    if new_remaining <= Decimal("0"):
        return DebtState.CLOSED.value
    return DebtState.PARTIAL.value


def can_apply_repayment(debt: Debt) -> bool:
    """True iff a repayment is legal in the debt's current state."""
    return debt.state in {DebtState.OPEN.value, DebtState.PARTIAL.value}


def can_cancel(debt: Debt) -> bool:
    """Cancellation is allowed from any non-terminal state."""
    return debt.state in {DebtState.OPEN.value, DebtState.PARTIAL.value}
