"""Story 5.5 — home_content end-to-end with display preference."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from currencies.models import ExchangeRate
from currencies.views import SESSION_DISPLAY_CURRENCY, SESSION_DISPLAY_MODE
from transactions.tests.factories import TransactionFactory


def _seed_user_with_mixed_currencies() -> User:
    user = User.objects.create(
        telegram_id=901,
        first_name="Eric",
        onboarded_at=timezone.now(),
        default_currency="UZS",
        show_converted=True,
    )
    today = date.today()
    ExchangeRate.objects.create(currency="USD", rate_to_uzs=Decimal("12500"), date=today)
    ExchangeRate.objects.create(currency="RUB", rate_to_uzs=Decimal("125"), date=today)
    TransactionFactory(
        user=user, type="income", amount=Decimal("1000000"), currency="UZS", date=today
    )
    TransactionFactory(user=user, type="income", amount=Decimal("100"), currency="USD", date=today)
    return user


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_shows_converted_aggregate_when_user_prefers() -> None:
    user = _seed_user_with_mixed_currencies()
    client = Client()
    init_data = _make_init_data(user_id=user.telegram_id, first_name="Eric")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    # 1_000_000 + 100*12500 = 2_250_000 UZS
    assert "2.25 mln UZS" in body
    assert "Manba valyutalar" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_falls_back_to_raw_when_rates_missing(monkeypatch) -> None:
    # The view self-heals an empty rates table by calling update_rates_if_stale.
    # Stub it so the test doesn't hit live CBU.uz and stays hermetic — we still
    # exercise the fallback path that triggers when the fetch can't populate
    # rates (CBU outage, no network, etc.).
    import core.views as _core_views

    monkeypatch.setattr(_core_views, "update_rates_if_stale", lambda: False)

    user = User.objects.create(
        telegram_id=902,
        first_name="Eric",
        onboarded_at=timezone.now(),
        default_currency="UZS",
        show_converted=True,
    )
    TransactionFactory(
        user=user, type="income", amount=Decimal("100"), currency="USD", date=date.today()
    )
    client = Client()
    init_data = _make_init_data(user_id=user.telegram_id, first_name="Eric")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    # No rates → falls back to raw UZS display (zero) + per-currency USD row.
    assert "Sof balans" in body
    assert "Boshqa valyutalar" in body
    assert "100 USD" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_session_override_picks_display_currency() -> None:
    user = _seed_user_with_mixed_currencies()
    client = Client()
    session = client.session
    session[SESSION_DISPLAY_CURRENCY] = "USD"
    session[SESSION_DISPLAY_MODE] = "converted"
    session.save()
    init_data = _make_init_data(user_id=user.telegram_id, first_name="Eric")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    # 1_000_000 UZS / 12500 + 100 USD = 80 + 100 = 180 USD
    assert "180" in body
    assert "USD" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_renders_stale_banner_when_rates_old() -> None:
    user = _seed_user_with_mixed_currencies()
    # Wipe today's rates → only stale (yesterday's) ones remain.
    ExchangeRate.objects.all().delete()
    ExchangeRate.objects.create(
        currency="USD",
        rate_to_uzs=Decimal("12500"),
        date=date.today().replace(day=1),  # very old
    )
    ExchangeRate.objects.create(
        currency="RUB",
        rate_to_uzs=Decimal("125"),
        date=date.today().replace(day=1),
    )
    client = Client()
    init_data = _make_init_data(user_id=user.telegram_id, first_name="Eric")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    assert "Valyuta kursi" in body
    assert "kun eski" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_shows_switcher_pill() -> None:
    user = User.objects.create(
        telegram_id=903,
        first_name="Eric",
        onboarded_at=timezone.now(),
    )
    client = Client()
    init_data = _make_init_data(user_id=user.telegram_id, first_name="Eric")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    assert "Valyutani almashtirish" in body
    assert "Mahalliy valyutalarda ko'rsatish" in body
    assert "Default valyutaga aylantirish" in body
