"""Story 4.1 — Debt model + queryset + constraints."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction as db_transaction

from debts.models import ACTIVE_STATES, Debt, DebtRepayment, DebtState
from debts.tests.factories import DebtFactory, DebtRepaymentFactory
from transactions.tests.factories import UserFactory

# ---------- Field & constraint sanity ----------


@pytest.mark.django_db
def test_debt_original_amount_must_be_positive() -> None:
    user = UserFactory()
    with db_transaction.atomic(), pytest.raises(IntegrityError):
        Debt.objects.create(
            user=user,
            direction="lent",
            counterparty="Karim",
            original_amount=Decimal("0"),
            remaining_amount=Decimal("0"),
            currency="UZS",
            state=DebtState.OPEN.value,
        )


@pytest.mark.django_db
def test_debt_remaining_amount_cannot_be_negative() -> None:
    user = UserFactory()
    with db_transaction.atomic(), pytest.raises(IntegrityError):
        Debt.objects.create(
            user=user,
            direction="lent",
            counterparty="Karim",
            original_amount=Decimal("100"),
            remaining_amount=Decimal("-1"),
            currency="UZS",
        )


@pytest.mark.django_db
def test_debt_remaining_amount_cannot_exceed_original() -> None:
    user = UserFactory()
    with db_transaction.atomic(), pytest.raises(IntegrityError):
        Debt.objects.create(
            user=user,
            direction="lent",
            counterparty="Karim",
            original_amount=Decimal("100"),
            remaining_amount=Decimal("200"),
            currency="UZS",
        )


@pytest.mark.django_db
def test_repayment_amount_must_be_positive() -> None:
    debt = DebtFactory()
    with db_transaction.atomic(), pytest.raises(IntegrityError):
        DebtRepayment.objects.create(
            debt=debt,
            amount=Decimal("0"),
            repaid_at=debt.created_at,
        )


def test_debt_direction_choices() -> None:
    found = {value for value, _label in Debt._meta.get_field("direction").choices}
    assert {"lent", "borrowed"} == found


def test_debt_state_choices() -> None:
    found = {value for value, _label in Debt._meta.get_field("state").choices}
    assert {"open", "partial", "closed", "cancelled"} == found


@pytest.mark.django_db
def test_debt_default_state_is_open() -> None:
    debt = DebtFactory()
    assert debt.state == DebtState.OPEN.value
    assert debt.is_active
    assert not debt.is_terminal


# ---------- Manager ----------


@pytest.mark.django_db
def test_for_user_isolates_owners() -> None:
    alice = UserFactory(telegram_id=1)
    bob = UserFactory(telegram_id=2)
    DebtFactory(user=alice)
    DebtFactory(user=alice)
    DebtFactory(user=bob)
    assert Debt.objects.for_user(alice).count() == 2
    assert Debt.objects.for_user(bob).count() == 1


@pytest.mark.django_db
def test_queryset_filters_lent_borrowed_active() -> None:
    user = UserFactory()
    open_lent = DebtFactory(user=user, direction="lent", state=DebtState.OPEN.value)
    DebtFactory(user=user, direction="borrowed", state=DebtState.OPEN.value)
    DebtFactory(user=user, direction="lent", state=DebtState.CLOSED.value)
    DebtFactory(user=user, direction="lent", state=DebtState.CANCELLED.value)

    active = Debt.objects.for_user(user).active()
    assert active.count() == 2
    assert open_lent in Debt.objects.for_user(user).active().lent()
    assert Debt.objects.for_user(user).active().borrowed().count() == 1


def test_active_states_includes_open_and_partial() -> None:
    assert {"open", "partial"} == ACTIVE_STATES


# ---------- Indexes ----------


def test_required_indexes_declared() -> None:
    declared = {tuple(idx.fields) for idx in Debt._meta.indexes}
    assert ("user", "state", "direction") in declared


# ---------- Repayment ----------


@pytest.mark.django_db
def test_debt_repayments_relationship() -> None:
    debt = DebtFactory()
    DebtRepaymentFactory(debt=debt, amount=Decimal("1000"))
    DebtRepaymentFactory(debt=debt, amount=Decimal("2000"))
    assert debt.repayments.count() == 2
