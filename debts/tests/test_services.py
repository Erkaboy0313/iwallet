"""Story 4.1 — Debt service layer (create / repay / cancel) end-to-end."""

from decimal import Decimal

import pytest

from debts.exceptions import (
    CurrencyMismatchError,
    DebtAlreadyClosedError,
    InvalidDebtAmountError,
    RepaymentExceedsRemainingError,
)
from debts.models import DebtState
from debts.services import apply_repayment, cancel_debt, create_debt
from debts.tests.factories import DebtFactory
from transactions.tests.factories import UserFactory

# ---------- create_debt ----------


@pytest.mark.django_db
def test_create_debt_persists_open_with_full_remaining() -> None:
    user = UserFactory()
    debt = create_debt(
        user=user,
        direction="lent",
        counterparty="Akram",
        amount=Decimal("1000000"),
        currency="UZS",
    )
    assert debt.pk is not None
    assert debt.state == DebtState.OPEN.value
    assert debt.original_amount == Decimal("1000000")
    assert debt.remaining_amount == Decimal("1000000")
    assert debt.counterparty == "Akram"


@pytest.mark.django_db
def test_create_debt_strips_counterparty_whitespace() -> None:
    user = UserFactory()
    debt = create_debt(
        user=user,
        direction="borrowed",
        counterparty="  Karim  ",
        amount=Decimal("500000"),
    )
    assert debt.counterparty == "Karim"


@pytest.mark.django_db
def test_create_debt_rejects_zero_amount() -> None:
    user = UserFactory()
    with pytest.raises(InvalidDebtAmountError):
        create_debt(user=user, direction="lent", counterparty="X", amount=Decimal("0"))


@pytest.mark.django_db
def test_create_debt_rejects_negative_amount() -> None:
    user = UserFactory()
    with pytest.raises(InvalidDebtAmountError):
        create_debt(user=user, direction="lent", counterparty="X", amount=Decimal("-10"))


@pytest.mark.django_db
def test_create_debt_rejects_empty_counterparty() -> None:
    user = UserFactory()
    with pytest.raises(InvalidDebtAmountError):
        create_debt(user=user, direction="lent", counterparty="   ", amount=Decimal("10"))


@pytest.mark.django_db
def test_create_debt_rejects_unknown_direction() -> None:
    user = UserFactory()
    with pytest.raises(InvalidDebtAmountError):
        create_debt(user=user, direction="sideways", counterparty="X", amount=Decimal("10"))


# ---------- apply_repayment — happy path ----------


@pytest.mark.django_db
def test_partial_repayment_open_to_partial_state() -> None:
    debt = DebtFactory(
        original_amount=Decimal("100000"),
        remaining_amount=Decimal("100000"),
        state=DebtState.OPEN.value,
    )
    debt, repayment = apply_repayment(debt=debt, amount=Decimal("30000"))
    assert debt.state == DebtState.PARTIAL.value
    assert debt.remaining_amount == Decimal("70000")
    assert repayment.amount == Decimal("30000")


@pytest.mark.django_db
def test_full_repayment_open_to_closed_state() -> None:
    debt = DebtFactory(
        original_amount=Decimal("50000"),
        remaining_amount=Decimal("50000"),
    )
    debt, _ = apply_repayment(debt=debt, amount=Decimal("50000"))
    assert debt.state == DebtState.CLOSED.value
    assert debt.remaining_amount == Decimal("0")


@pytest.mark.django_db
def test_two_partial_repayments_to_closed() -> None:
    debt = DebtFactory(
        original_amount=Decimal("100"),
        remaining_amount=Decimal("100"),
    )
    debt, _ = apply_repayment(debt=debt, amount=Decimal("40"))
    assert debt.state == DebtState.PARTIAL.value
    debt, _ = apply_repayment(debt=debt, amount=Decimal("60"))
    assert debt.state == DebtState.CLOSED.value
    assert debt.remaining_amount == Decimal("0")
    assert debt.repayments.count() == 2


@pytest.mark.django_db
def test_partial_remains_partial_when_not_yet_cleared() -> None:
    debt = DebtFactory(
        original_amount=Decimal("100"),
        remaining_amount=Decimal("100"),
    )
    debt, _ = apply_repayment(debt=debt, amount=Decimal("40"))
    debt, _ = apply_repayment(debt=debt, amount=Decimal("30"))
    assert debt.state == DebtState.PARTIAL.value
    assert debt.remaining_amount == Decimal("30")


# ---------- apply_repayment — errors ----------


@pytest.mark.django_db
def test_repayment_on_closed_debt_raises() -> None:
    debt = DebtFactory(state=DebtState.CLOSED.value, remaining_amount=Decimal("0"))
    with pytest.raises(DebtAlreadyClosedError):
        apply_repayment(debt=debt, amount=Decimal("10"))


@pytest.mark.django_db
def test_repayment_on_cancelled_debt_raises() -> None:
    debt = DebtFactory(state=DebtState.CANCELLED.value)
    with pytest.raises(DebtAlreadyClosedError):
        apply_repayment(debt=debt, amount=Decimal("10"))


@pytest.mark.django_db
def test_repayment_exceeding_remaining_raises() -> None:
    debt = DebtFactory(
        original_amount=Decimal("100"),
        remaining_amount=Decimal("100"),
    )
    with pytest.raises(RepaymentExceedsRemainingError):
        apply_repayment(debt=debt, amount=Decimal("150"))


@pytest.mark.django_db
def test_repayment_currency_mismatch_raises() -> None:
    debt = DebtFactory(currency="UZS")
    with pytest.raises(CurrencyMismatchError):
        apply_repayment(debt=debt, amount=Decimal("10"), currency="USD")


@pytest.mark.django_db
def test_repayment_same_currency_explicit_ok() -> None:
    debt = DebtFactory(currency="UZS")
    debt, _ = apply_repayment(debt=debt, amount=Decimal("10"), currency="UZS")
    assert debt.state == DebtState.PARTIAL.value


@pytest.mark.django_db
def test_repayment_zero_amount_raises() -> None:
    debt = DebtFactory()
    with pytest.raises(InvalidDebtAmountError):
        apply_repayment(debt=debt, amount=Decimal("0"))


@pytest.mark.django_db
def test_repayment_negative_amount_raises() -> None:
    debt = DebtFactory()
    with pytest.raises(InvalidDebtAmountError):
        apply_repayment(debt=debt, amount=Decimal("-1"))


# ---------- cancel_debt ----------


@pytest.mark.django_db
def test_cancel_open_debt_sets_state_and_reason() -> None:
    debt = DebtFactory(state=DebtState.OPEN.value)
    cancelled = cancel_debt(debt=debt, reason="forgiven")
    assert cancelled.state == DebtState.CANCELLED.value
    assert cancelled.cancelled_reason == "forgiven"


@pytest.mark.django_db
def test_cancel_partial_debt_allowed() -> None:
    debt = DebtFactory(
        original_amount=Decimal("100"),
        remaining_amount=Decimal("100"),
    )
    apply_repayment(debt=debt, amount=Decimal("30"))
    debt.refresh_from_db()
    assert debt.state == DebtState.PARTIAL.value
    cancelled = cancel_debt(debt=debt, reason="forgiven")
    assert cancelled.state == DebtState.CANCELLED.value


@pytest.mark.django_db
def test_cancel_closed_debt_raises() -> None:
    debt = DebtFactory(state=DebtState.CLOSED.value, remaining_amount=Decimal("0"))
    with pytest.raises(DebtAlreadyClosedError):
        cancel_debt(debt=debt, reason="forgiven")


@pytest.mark.django_db
def test_cancel_already_cancelled_raises() -> None:
    debt = DebtFactory(state=DebtState.CANCELLED.value)
    with pytest.raises(DebtAlreadyClosedError):
        cancel_debt(debt=debt, reason="forgiven")


@pytest.mark.django_db
def test_cancel_truncates_long_reason() -> None:
    debt = DebtFactory()
    cancelled = cancel_debt(debt=debt, reason="x" * 200)
    assert len(cancelled.cancelled_reason) == 64
