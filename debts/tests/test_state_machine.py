"""Story 4.1 — Debt state machine transitions."""

from decimal import Decimal

from debts.models import Debt, DebtState
from debts.state_machine import (
    can_apply_repayment,
    can_cancel,
    next_state_after_repayment,
)


def _debt(state: str, remaining: Decimal = Decimal("100")) -> Debt:
    """Unsaved Debt instance — state machine only inspects fields."""
    return Debt(
        direction="lent",
        counterparty="X",
        original_amount=Decimal("100"),
        remaining_amount=remaining,
        currency="UZS",
        state=state,
    )


def test_open_to_partial_when_repayment_below_remaining() -> None:
    debt = _debt(DebtState.OPEN.value, Decimal("100"))
    debt.remaining_amount = Decimal("60")  # after applying 40
    assert next_state_after_repayment(debt, Decimal("0")) == DebtState.PARTIAL.value


def test_open_to_closed_when_repayment_equals_remaining() -> None:
    debt = _debt(DebtState.OPEN.value, Decimal("100"))
    debt.remaining_amount = Decimal("0")
    assert next_state_after_repayment(debt, Decimal("0")) == DebtState.CLOSED.value


def test_partial_remains_partial_when_more_owed() -> None:
    debt = _debt(DebtState.PARTIAL.value, Decimal("40"))
    debt.remaining_amount = Decimal("10")
    assert next_state_after_repayment(debt, Decimal("0")) == DebtState.PARTIAL.value


def test_partial_to_closed_when_repayment_clears_remaining() -> None:
    debt = _debt(DebtState.PARTIAL.value, Decimal("40"))
    debt.remaining_amount = Decimal("0")
    assert next_state_after_repayment(debt, Decimal("0")) == DebtState.CLOSED.value


def test_can_apply_repayment_only_in_active_states() -> None:
    assert can_apply_repayment(_debt(DebtState.OPEN.value))
    assert can_apply_repayment(_debt(DebtState.PARTIAL.value))
    assert not can_apply_repayment(_debt(DebtState.CLOSED.value))
    assert not can_apply_repayment(_debt(DebtState.CANCELLED.value))


def test_can_cancel_only_in_active_states() -> None:
    assert can_cancel(_debt(DebtState.OPEN.value))
    assert can_cancel(_debt(DebtState.PARTIAL.value))
    assert not can_cancel(_debt(DebtState.CLOSED.value))
    assert not can_cancel(_debt(DebtState.CANCELLED.value))
