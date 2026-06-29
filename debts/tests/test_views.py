"""Qarzlar list view — v0.7 simplified.

Qarzlar is now a flat, filtered view of debt-type Transactions. There is
no separate Debt aggregate; tabs just narrow by Transaction.type.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from transactions.tests.factories import TransactionFactory


def _user(telegram_id: int = 7) -> User:
    return User.objects.create(
        telegram_id=telegram_id, first_name="Eric", onboarded_at=timezone.now()
    )


def _init(user_id: int) -> str:
    return _make_init_data(user_id=user_id)


@pytest.mark.django_db
def test_debts_list_requires_auth() -> None:
    client = Client()
    response = client.get(reverse("debts:list"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_default_tab_is_lent() -> None:
    """No ?tab query → "Menga qarzdor" tab is active."""
    user = _user(10)
    TransactionFactory(
        user=user,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        date=date.today(),
    )
    client = Client()
    response = client.get(
        reverse("debts:list"),
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Both tab labels render; lent is the default active.
    assert "Menga qarzdor" in body
    assert "Men qarzdorman" in body
    assert "Akram" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_filters_to_active_tab() -> None:
    """Each tab only shows transactions matching its direction."""
    user = _user(11)
    TransactionFactory(
        user=user,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        date=date.today(),
    )
    TransactionFactory(
        user=user,
        type="debt_borrowed",
        counterparty="Karim",
        amount=Decimal("50000"),
        date=date.today(),
    )
    client = Client()
    lent = client.get(
        reverse("debts:list") + "?tab=debt_lent",
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    ).content.decode("utf-8")
    borrowed = client.get(
        reverse("debts:list") + "?tab=debt_borrowed",
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    ).content.decode("utf-8")
    assert "Akram" in lent
    assert "Karim" not in lent
    assert "Karim" in borrowed
    assert "Akram" not in borrowed


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_ignores_non_debt_transactions() -> None:
    """Income / expense rows never bleed into Qarzlar."""
    user = _user(12)
    TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("500000"),
        date=date.today(),
        note="oylik",
    )
    client = Client()
    body = client.get(
        reverse("debts:list"),
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    ).content.decode("utf-8")
    assert "oylik" not in body
    # Empty state copy for the lent tab is shown.
    assert "Qarz yo&#x27;q" in body or "Qarz yo'q" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_isolates_users() -> None:
    """One user's debt-type Transactions never appear for another user."""
    me = _user(13)
    other = _user(14)
    TransactionFactory(
        user=other,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        date=date.today(),
    )
    client = Client()
    body = client.get(
        reverse("debts:list"),
        headers={"X-Telegram-InitData": _init(me.telegram_id)},
    ).content.decode("utf-8")
    assert "Akram" not in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_new_qarz_button_deeplinks_into_add() -> None:
    """+ Yangi qarz on the lent tab points at /transactions/add/?type=debt_lent."""
    user = _user(15)
    client = Client()
    lent_body = client.get(
        reverse("debts:list") + "?tab=debt_lent",
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    ).content.decode("utf-8")
    borrowed_body = client.get(
        reverse("debts:list") + "?tab=debt_borrowed",
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    ).content.decode("utf-8")
    assert "type=debt_lent" in lent_body
    assert "type=debt_borrowed" in borrowed_body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_add_page_honours_type_query_param() -> None:
    """Qarzlar deep-link pre-selects the debt type on Add page."""
    user = _user(16)
    client = Client()
    body = client.get(
        reverse("transactions:add") + "?type=debt_lent",
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    ).content.decode("utf-8")
    # Initial form data renders the radio with the matching value checked.
    assert 'value="debt_lent"' in body
    assert "checked" in body
