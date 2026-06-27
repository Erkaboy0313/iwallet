"""Story 1.4 — add_transaction_view integration tests."""

from datetime import date

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from transactions.models import Transaction


def _post_payload(**overrides) -> dict:
    data = {
        "type": "expense",
        "amount": "25000.00",
        "currency": "UZS",
        "date": date.today().isoformat(),
        "note": "taxi",
        "category_slug": "",
        "counterparty": "",
    }
    data.update(overrides)
    return data


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_get_renders_form_for_authenticated_user() -> None:
    client = Client()
    init_data = _make_init_data(user_id=7)
    response = client.get(
        reverse("transactions:add"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Yangi tranzaksiya" in body
    assert 'name="amount"' in body
    assert 'name="currency"' in body


@pytest.mark.django_db
def test_add_endpoint_rejects_anonymous() -> None:
    client = Client()
    response = client.get(reverse("transactions:add"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_post_valid_creates_transaction_and_redirects_home() -> None:
    client = Client()
    init_data = _make_init_data(user_id=7)
    response = client.post(
        reverse("transactions:add"),
        data=_post_payload(),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == reverse("core:home")
    assert "HX-Trigger" in response.headers
    assert Transaction.objects.filter(user__telegram_id=7).count() == 1


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_post_invalid_returns_422_with_form() -> None:
    """Zero amount fails validation; htmx swap restores the form with error markup."""
    client = Client()
    init_data = _make_init_data(user_id=7)
    response = client.post(
        reverse("transactions:add"),
        data=_post_payload(amount="0"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 422
    body = response.content.decode("utf-8")
    assert "Summa" in body  # form rendered
    assert Transaction.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_post_debt_requires_counterparty() -> None:
    client = Client()
    init_data = _make_init_data(user_id=7)
    response = client.post(
        reverse("transactions:add"),
        data=_post_payload(type="debt_lent", counterparty=""),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 422
    body = response.content.decode("utf-8")
    assert "Kim bilan" in body
    assert Transaction.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_post_debt_with_counterparty_persists_name() -> None:
    client = Client()
    init_data = _make_init_data(user_id=7)
    response = client.post(
        reverse("transactions:add"),
        data=_post_payload(type="debt_lent", counterparty="Akram"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    tx = Transaction.objects.get(user__telegram_id=7)
    assert tx.type == "debt_lent"
    assert tx.counterparty == "Akram"
