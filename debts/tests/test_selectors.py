"""Story 4.3 — read-side selectors for the debts screen."""

from decimal import Decimal

import pytest

from debts.models import DebtState
from debts.selectors import (
    active_debts_for,
    debt_status_summary,
    get_user_debt,
    initials_for,
    totals_by_currency,
)
from debts.tests.factories import DebtFactory
from transactions.tests.factories import UserFactory

# ---------- active_debts_for ----------


@pytest.mark.django_db
def test_active_debts_for_filters_by_direction_and_state() -> None:
    user = UserFactory()
    open_lent = DebtFactory(user=user, direction="lent", state=DebtState.OPEN.value)
    DebtFactory(user=user, direction="borrowed", state=DebtState.OPEN.value)
    DebtFactory(user=user, direction="lent", state=DebtState.CLOSED.value)
    DebtFactory(user=user, direction="lent", state=DebtState.CANCELLED.value)
    partial_lent = DebtFactory(user=user, direction="lent", state=DebtState.PARTIAL.value)

    result = list(active_debts_for(user, direction="lent"))
    assert open_lent in result
    assert partial_lent in result
    assert len(result) == 2


@pytest.mark.django_db
def test_active_debts_for_isolates_users() -> None:
    a = UserFactory(telegram_id=100)
    b = UserFactory(telegram_id=200)
    DebtFactory(user=a, direction="lent")
    DebtFactory(user=b, direction="lent")
    assert active_debts_for(a, direction="lent").count() == 1


@pytest.mark.django_db
def test_active_debts_for_rejects_unknown_direction() -> None:
    user = UserFactory()
    with pytest.raises(ValueError):
        active_debts_for(user, direction="sideways")


# ---------- totals_by_currency ----------


@pytest.mark.django_db
def test_totals_by_currency_sums_per_currency() -> None:
    user = UserFactory()
    DebtFactory(user=user, direction="lent", currency="UZS", remaining_amount=Decimal("100"))
    DebtFactory(user=user, direction="lent", currency="UZS", remaining_amount=Decimal("50"))
    DebtFactory(user=user, direction="lent", currency="USD", remaining_amount=Decimal("20"))
    qs = active_debts_for(user, direction="lent")
    totals = totals_by_currency(qs)
    summary = {t.currency: t.total for t in totals}
    assert summary == {"UZS": Decimal("150"), "USD": Decimal("20")}


# ---------- debt_status_summary ----------


@pytest.mark.django_db
def test_status_summary_counts_and_per_currency_totals() -> None:
    user = UserFactory()
    DebtFactory(user=user, direction="lent", currency="UZS", remaining_amount=Decimal("100"))
    DebtFactory(user=user, direction="lent", currency="UZS", remaining_amount=Decimal("200"))
    DebtFactory(user=user, direction="borrowed", currency="UZS", remaining_amount=Decimal("50"))
    # Closed should be skipped.
    DebtFactory(
        user=user,
        direction="lent",
        state=DebtState.CLOSED.value,
        remaining_amount=Decimal("0"),
    )
    summary = debt_status_summary(user)
    assert summary.open_lent_count == 2
    assert summary.open_borrowed_count == 1
    assert summary.lent_remaining_by_currency == {"UZS": Decimal("300")}
    assert summary.borrowed_remaining_by_currency == {"UZS": Decimal("50")}
    assert summary.has_any


@pytest.mark.django_db
def test_status_summary_empty() -> None:
    user = UserFactory()
    summary = debt_status_summary(user)
    assert summary.open_lent_count == 0
    assert summary.open_borrowed_count == 0
    assert not summary.has_any


# ---------- get_user_debt ----------


@pytest.mark.django_db
def test_get_user_debt_returns_only_own() -> None:
    owner = UserFactory(telegram_id=1)
    stranger = UserFactory(telegram_id=2)
    debt = DebtFactory(user=owner)
    assert get_user_debt(owner, debt.pk) == debt
    assert get_user_debt(stranger, debt.pk) is None


# ---------- initials_for ----------


def test_initials_for_single_word() -> None:
    assert initials_for("Akram") == "AK"


def test_initials_for_two_words() -> None:
    assert initials_for("Akram Tursun") == "AT"


def test_initials_for_three_words_takes_first_and_last() -> None:
    assert initials_for("Akram Test Tursun") == "AT"


def test_initials_for_empty() -> None:
    assert initials_for("") == "?"
    assert initials_for("   ") == "?"
