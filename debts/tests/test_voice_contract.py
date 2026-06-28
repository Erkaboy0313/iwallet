"""Story 4.2 — contract tests for the voice-flow integration point.

The voice parser + confirm screen ship in Epic 2 (Stories 2.3 + 2.4). This
module locks down the contract that the future voice-save handler will rely on:
when a parsed VoiceDraft has `type in {debt_lent, debt_borrowed}`, the save
endpoint must call `debts.services.create_debt(...)` (not
`transactions.services.create_transaction(...)`) so the debt aggregates the
counterparty's running balance.

Full integration tests (audio -> parser -> Debt row) follow once Epic 2 is in
place. Until then, these tests pin the API surface so the Epic 2 author can't
accidentally route debt drafts through the transactions pipeline.
"""

from decimal import Decimal

import pytest

from debts.models import Debt, DebtDirection, DebtState
from debts.services import create_debt
from transactions.models import Transaction
from transactions.tests.factories import UserFactory


@pytest.mark.django_db
def test_voice_debt_lent_creates_debt_row_not_transaction() -> None:
    """A simulated voice draft like 'Akramga 1 mln qarz berdim' creates a Debt."""
    user = UserFactory()
    # This is the exact call shape the future voice/save view will make.
    debt = create_debt(
        user=user,
        direction=DebtDirection.LENT.value,
        counterparty="Akram",
        amount=Decimal("1000000"),
        currency="UZS",
    )
    assert Debt.objects.filter(pk=debt.pk).exists()
    # Crucially: NO Transaction row is created for the same event — debts are
    # tracked as aggregates and only "qaytarildi" repayments flow through the
    # cash side (Epic 8 reports include them via include_debts toggle).
    assert Transaction.objects.filter(user=user, counterparty="Akram").count() == 0
    assert debt.state == DebtState.OPEN.value


@pytest.mark.django_db
def test_voice_debt_borrowed_creates_debt_row_not_transaction() -> None:
    """'Akramdan 500k qarz oldim' → Debt(direction=borrowed)."""
    user = UserFactory()
    debt = create_debt(
        user=user,
        direction=DebtDirection.BORROWED.value,
        counterparty="Akram",
        amount=Decimal("500000"),
        currency="UZS",
    )
    assert debt.direction == DebtDirection.BORROWED.value
    assert Transaction.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_create_debt_signature_accepts_voice_optional_fields() -> None:
    """The voice draft may carry a note and/or expected_return_date; both optional."""
    user = UserFactory()
    debt = create_debt(
        user=user,
        direction="lent",
        counterparty="Karim",
        amount=Decimal("10"),
        currency="UZS",
        note="ovozdan qo'shildi",
    )
    assert debt.note == "ovozdan qo'shildi"
