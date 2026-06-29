"""Qarzlar list/new/settle — v0.7 simplified.

Qarzlar is a flat, filtered view of debt-type Transactions. Status badges
("Ochiq" / "Yopilgan") come from `settled_at`; Yopish action flips the
flag and spawns a paired income/expense Transaction.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from transactions.models import Transaction
from transactions.tests.factories import TransactionFactory


def _user(telegram_id: int = 7) -> User:
    return User.objects.create(
        telegram_id=telegram_id, first_name="Eric", onboarded_at=timezone.now()
    )


def _init(user_id: int) -> str:
    return _make_init_data(user_id=user_id)


# ---------- list ----------


@pytest.mark.django_db
def test_debts_list_requires_auth() -> None:
    client = Client()
    response = client.get(reverse("debts:list"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_default_tab_is_lent() -> None:
    user = _user(10)
    TransactionFactory(
        user=user,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        date=date.today(),
    )
    body = (
        Client()
        .get(
            reverse("debts:list"),
            headers={"X-Telegram-InitData": _init(user.telegram_id)},
        )
        .content.decode("utf-8")
    )
    assert "Menga qarzdor" in body
    assert "Men qarzdorman" in body
    assert "Akram" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_filters_to_active_tab() -> None:
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
    assert "Akram" in lent and "Karim" not in lent
    assert "Karim" in borrowed and "Akram" not in borrowed


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_shows_open_badge_for_unsettled_debts() -> None:
    user = _user(12)
    TransactionFactory(
        user=user,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        date=date.today(),
    )
    body = (
        Client()
        .get(
            reverse("debts:list"),
            headers={"X-Telegram-InitData": _init(user.telegram_id)},
        )
        .content.decode("utf-8")
    )
    assert "Ochiq" in body
    assert "Yopilgan" not in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_shows_settled_badge_for_settled_debts() -> None:
    user = _user(13)
    TransactionFactory(
        user=user,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        date=date.today(),
        settled_at=timezone.now(),
    )
    body = (
        Client()
        .get(
            reverse("debts:list"),
            headers={"X-Telegram-InitData": _init(user.telegram_id)},
        )
        .content.decode("utf-8")
    )
    assert "Yopilgan" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_isolates_users() -> None:
    me = _user(14)
    other = _user(15)
    TransactionFactory(
        user=other,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        date=date.today(),
    )
    body = (
        Client()
        .get(
            reverse("debts:list"),
            headers={"X-Telegram-InitData": _init(me.telegram_id)},
        )
        .content.decode("utf-8")
    )
    assert "Akram" not in body


# ---------- new (POST quick form) ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_new_debt_creates_transaction_with_tab_direction() -> None:
    user = _user(16)
    response = Client().post(
        reverse("debts:new"),
        data={"tab": "debt_lent", "counterparty": "Akram", "amount": "100000", "currency": "UZS"},
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    )
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == reverse("debts:list") + "?tab=debt_lent"
    tx = Transaction.objects.get(user=user)
    assert tx.type == "debt_lent"
    assert tx.counterparty == "Akram"
    assert tx.amount == Decimal("100000")
    assert tx.settled_at is None


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_new_debt_rejects_empty_counterparty() -> None:
    user = _user(17)
    response = Client().post(
        reverse("debts:new"),
        data={"tab": "debt_lent", "counterparty": "", "amount": "100000", "currency": "UZS"},
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    )
    assert response.status_code == 422
    assert Transaction.objects.filter(user=user).count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_new_debt_rejects_zero_amount() -> None:
    user = _user(18)
    response = Client().post(
        reverse("debts:new"),
        data={"tab": "debt_lent", "counterparty": "Akram", "amount": "0", "currency": "UZS"},
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    )
    assert response.status_code == 422
    assert Transaction.objects.filter(user=user).count() == 0


# ---------- settle ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_settle_lent_marks_settled_and_spawns_income() -> None:
    """Settling a debt_lent (someone paid me back) creates an income twin."""
    user = _user(19)
    tx = TransactionFactory(
        user=user,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        currency="UZS",
        date=date.today(),
    )
    response = Client().post(
        reverse("debts:settle", args=[tx.id]),
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    )
    assert response.status_code == 200
    tx.refresh_from_db()
    assert tx.settled_at is not None
    # Counter row created: income, same amount, auto-note tied to counterparty.
    counter = Transaction.objects.filter(user=user, type="income").get()
    assert counter.amount == Decimal("100000")
    assert counter.counterparty == "Akram"
    assert "Qarz qaytarib oldim" in counter.note
    assert "Akram" in counter.note


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_settle_borrowed_marks_settled_and_spawns_expense() -> None:
    """Settling a debt_borrowed (I paid them back) creates an expense twin."""
    user = _user(20)
    tx = TransactionFactory(
        user=user,
        type="debt_borrowed",
        counterparty="Karim",
        amount=Decimal("50000"),
        currency="UZS",
        date=date.today(),
    )
    Client().post(
        reverse("debts:settle", args=[tx.id]),
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    )
    tx.refresh_from_db()
    assert tx.settled_at is not None
    counter = Transaction.objects.filter(user=user, type="expense").get()
    assert counter.amount == Decimal("50000")
    assert "Qarz qaytarib berdim" in counter.note
    assert "Karim" in counter.note


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_settle_already_settled_returns_422() -> None:
    user = _user(21)
    tx = TransactionFactory(
        user=user,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        date=date.today(),
        settled_at=timezone.now(),
    )
    response = Client().post(
        reverse("debts:settle", args=[tx.id]),
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    )
    assert response.status_code == 422


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_settle_non_debt_transaction_404() -> None:
    """Trying to settle an income/expense row 404s — not a debt."""
    user = _user(22)
    tx = TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("100000"),
        date=date.today(),
    )
    response = Client().post(
        reverse("debts:settle", args=[tx.id]),
        headers={"X-Telegram-InitData": _init(user.telegram_id)},
    )
    assert response.status_code == 404


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_settle_other_users_debt_404() -> None:
    me = _user(23)
    other = _user(24)
    tx = TransactionFactory(
        user=other,
        type="debt_lent",
        counterparty="Akram",
        amount=Decimal("100000"),
        date=date.today(),
    )
    response = Client().post(
        reverse("debts:settle", args=[tx.id]),
        headers={"X-Telegram-InitData": _init(me.telegram_id)},
    )
    assert response.status_code == 404
