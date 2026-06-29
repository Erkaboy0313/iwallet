"""home_content end-to-end with the simplified v0.7 currency model.

- Balance hero ALWAYS aggregates into the selected display currency.
- Transactions, top-categories, history, reports stay in source currency.
- Switcher is a session-only preference; it never mutates user.default_currency.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from currencies.models import ExchangeRate
from currencies.views import SESSION_DISPLAY_CURRENCY
from transactions.tests.factories import TransactionFactory


def _seed_user_with_mixed_currencies() -> User:
    user = User.objects.create(
        telegram_id=901,
        first_name="Eric",
        onboarded_at=timezone.now(),
        default_currency="UZS",
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
def test_home_content_shows_aggregated_balance_in_default_currency() -> None:
    """Default currency UZS → hero aggregates everything into UZS."""
    user = _seed_user_with_mixed_currencies()
    client = Client()
    init_data = _make_init_data(user_id=user.telegram_id, first_name="Eric")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    # 1_000_000 + 100*12500 = 2_250_000 UZS aggregated into the hero amount.
    assert "2.25 mln UZS" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_falls_back_to_raw_when_rates_missing(monkeypatch) -> None:
    """No exchange rates → hero shows the user's default-currency total only."""
    import core.views as _core_views

    monkeypatch.setattr(_core_views, "update_rates_if_stale", lambda: False)

    user = User.objects.create(
        telegram_id=902,
        first_name="Eric",
        onboarded_at=timezone.now(),
        default_currency="UZS",
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
    assert "Sof balans" in body
    # User only has USD transactions and no UZS rate, so the hero falls back
    # to source-currency total. The per-currency strip is hidden with a single
    # source currency — UZS shows up in the headline directly.
    assert "0 UZS" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_session_currency_drives_hero_aggregation() -> None:
    """Picking USD in the switcher converts the headline into USD."""
    user = _seed_user_with_mixed_currencies()
    client = Client()
    session = client.session
    session[SESSION_DISPLAY_CURRENCY] = "USD"
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
def test_home_content_renders_stale_banner_when_rates_old(monkeypatch) -> None:
    import core.views as _core_views

    monkeypatch.setattr(_core_views, "update_rates_if_stale", lambda: False)

    user = _seed_user_with_mixed_currencies()
    # Wipe today's rates → only stale (very old) ones remain.
    ExchangeRate.objects.all().delete()
    ExchangeRate.objects.create(
        currency="USD",
        rate_to_uzs=Decimal("12500"),
        date=date.today().replace(day=1),
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
def test_home_content_shows_switcher_dropdown_options() -> None:
    """All 3 currencies are rendered as options in the switcher dropdown."""
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
    assert 'data-iw-currency="UZS"' in body
    assert 'data-iw-currency="USD"' in body
    assert 'data-iw-currency="RUB"' in body
    # Pre-computed totals are embedded for the JS-driven instant swap.
    assert "data-balance-uzs" in body
    assert "data-balance-usd" in body
    assert "data-balance-rub" in body
