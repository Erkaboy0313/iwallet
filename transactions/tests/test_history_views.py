"""Story 1.6 — history view + edit + delete + restore."""

from datetime import timedelta
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


# ---------- history_view ----------


@pytest.mark.django_db
def test_history_requires_auth() -> None:
    client = Client()
    response = client.get(reverse("transactions:history"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_history_renders_full_page_when_not_htmx() -> None:
    user = _user(10)
    TransactionFactory(user=user, note="taxi")
    client = Client()
    init = _make_init_data(user_id=10)

    response = client.get(
        reverse("transactions:history"),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Tarix" in body  # page heading
    assert "Hammasi" in body  # filter pill
    assert "taxi" in body  # transaction note rendered


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_history_returns_list_partial_when_htmx() -> None:
    user = _user(11)
    TransactionFactory(user=user, note="lunch")
    client = Client()
    init = _make_init_data(user_id=11)

    response = client.get(
        reverse("transactions:history"),
        headers={"X-Telegram-InitData": init, "HX-Request": "true"},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "lunch" in body
    # Page heading absent in partial
    assert "Tarix" not in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_history_filter_by_type_returns_subset() -> None:
    user = _user(12)
    TransactionFactory(user=user, type="income", note="oylik")
    TransactionFactory(user=user, type="expense", note="taxi")
    client = Client()
    init = _make_init_data(user_id=12)

    response = client.get(
        reverse("transactions:history") + "?type=income",
        headers={"X-Telegram-InitData": init, "HX-Request": "true"},
    )
    body = response.content.decode("utf-8")
    assert "oylik" in body
    assert "taxi" not in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_history_empty_state_shown_when_no_transactions() -> None:
    _user(13)
    client = Client()
    init = _make_init_data(user_id=13)

    response = client.get(
        reverse("transactions:history"),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Hozircha tranzaksiya yo'q" in body


# ---------- edit_transaction_view ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_get_pre_fills_form() -> None:
    user = _user(20)
    tx = TransactionFactory(user=user, amount=Decimal("12500"), note="qahva")
    client = Client()
    init = _make_init_data(user_id=20)

    response = client.get(
        reverse("transactions:edit", args=[tx.id]),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "qahva" in body
    assert "12500" in body or "12 500" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_post_valid_updates_and_redirects() -> None:
    user = _user(21)
    tx = TransactionFactory(user=user, amount=Decimal("10000"), note="")
    client = Client()
    init = _make_init_data(user_id=21)

    response = client.post(
        reverse("transactions:edit", args=[tx.id]),
        data={
            "type": tx.type,
            "amount": "15000",
            "currency": tx.currency,
            "date": tx.date.isoformat(),
            "note": "edited",
            "category_slug": "",
            "counterparty": "",
        },
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == reverse("transactions:history")
    tx.refresh_from_db()
    assert tx.amount == Decimal("15000")
    assert tx.note == "edited"


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_other_users_transaction_returns_404() -> None:
    owner = _user(22)
    intruder = User.objects.create(
        telegram_id=99, first_name="Stranger", onboarded_at=timezone.now()
    )
    tx = TransactionFactory(user=owner)
    client = Client()
    init = _make_init_data(user_id=intruder.telegram_id)

    response = client.get(
        reverse("transactions:edit", args=[tx.id]),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 404


# ---------- delete + restore ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_delete_soft_marks_and_redirects() -> None:
    user = _user(30)
    tx = TransactionFactory(user=user)
    client = Client()
    init = _make_init_data(user_id=30)

    response = client.post(
        reverse("transactions:delete", args=[tx.id]),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == reverse("transactions:history")
    tx.refresh_from_db()
    assert tx.is_deleted is True


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_restore_within_window_brings_transaction_back() -> None:
    user = _user(31)
    tx = TransactionFactory(
        user=user, is_deleted=True, deleted_at=timezone.now() - timedelta(hours=1)
    )
    client = Client()
    init = _make_init_data(user_id=31)

    response = client.post(
        reverse("transactions:restore", args=[tx.id]),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200
    tx.refresh_from_db()
    assert tx.is_deleted is False


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_restore_after_window_returns_410() -> None:
    user = _user(32)
    tx = TransactionFactory(
        user=user, is_deleted=True, deleted_at=timezone.now() - timedelta(days=8)
    )
    client = Client()
    init = _make_init_data(user_id=32)

    response = client.post(
        reverse("transactions:restore", args=[tx.id]),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 410


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_restore_on_live_row_returns_404() -> None:
    user = _user(33)
    tx = TransactionFactory(user=user)
    client = Client()
    init = _make_init_data(user_id=33)

    response = client.post(
        reverse("transactions:restore", args=[tx.id]),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 404
