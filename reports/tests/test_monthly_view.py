"""Story 8.3 — monthly view integration tests."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from currencies.models import ExchangeRate
from transactions.tests.factories import TransactionFactory


def _user(telegram_id: int = 7) -> User:
    return User.objects.create(
        telegram_id=telegram_id, first_name="Eric", onboarded_at=timezone.now()
    )


@pytest.mark.django_db
def test_monthly_requires_auth() -> None:
    client = Client()
    response = client.get(reverse("reports:monthly"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_monthly_renders_with_data() -> None:
    user = _user(820)
    today = timezone.localdate()
    TransactionFactory(user=user, type="expense", amount=Decimal("500"), date=today)
    TransactionFactory(user=user, type="income", amount=Decimal("2000"), date=today)
    client = Client()
    init = _make_init_data(user_id=820)

    response = client.get(
        reverse("reports:monthly"),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Oy" in body
    assert "Kirim" in body
    assert "Chiqim" in body
    # IO bars + pie SVGs.
    assert body.count("<svg") >= 2


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_monthly_empty_state() -> None:
    _user(821)
    client = Client()
    init = _make_init_data(user_id=821)

    response = client.get(
        reverse("reports:monthly"),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Bu oyda tranzaksiya yo'q" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_monthly_multi_currency_section_appears_when_data_present() -> None:
    user = _user(822)
    today = date(2026, 6, 15)
    ExchangeRate.objects.create(currency="USD", rate_to_uzs=Decimal("12500.00"), date=today)
    with patch("reports.views.timezone") as tz, patch("reports.services.timezone") as tz2:
        tz.localdate.return_value = today
        tz2.localdate.return_value = today
        TransactionFactory(
            user=user, type="income", amount=Decimal("100"), currency="USD", date=today
        )
        TransactionFactory(
            user=user, type="income", amount=Decimal("1000"), currency="UZS", date=today
        )
        client = Client()
        init = _make_init_data(user_id=822)

        response = client.get(
            reverse("reports:monthly") + "?month=2026-06",
            headers={"X-Telegram-InitData": init},
        )
    body = response.content.decode("utf-8")
    assert "Valyuta bo'yicha taqsimot" in body
    assert "USD" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_monthly_month_param_respected() -> None:
    user = _user(823)
    TransactionFactory(user=user, type="expense", amount=Decimal("777"), date=date(2026, 3, 15))
    client = Client()
    init = _make_init_data(user_id=823)

    response = client.get(
        reverse("reports:monthly") + "?month=2026-03",
        headers={"X-Telegram-InitData": init},
    )
    body = response.content.decode("utf-8")
    assert "Mart 2026" in body
    assert "777" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_monthly_garbage_month_falls_back_to_current() -> None:
    _user(824)
    client = Client()
    init = _make_init_data(user_id=824)

    response = client.get(
        reverse("reports:monthly") + "?month=garbage",
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_monthly_navigation_arrows_present() -> None:
    user = _user(825)
    TransactionFactory(user=user, type="expense", amount=Decimal("100"))
    client = Client()
    init = _make_init_data(user_id=825)

    response = client.get(
        reverse("reports:monthly"),
        headers={"X-Telegram-InitData": init},
    )
    body = response.content.decode("utf-8")
    assert "month=" in body
    assert "Avvalgi davr" in body
    assert "Keyingi davr" in body
