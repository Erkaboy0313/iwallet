"""home_content end-to-end with the simplified v0.7 currency model.

- Balance hero ALWAYS aggregates into the selected display currency.
- Transactions, top-categories, history, reports stay in source currency.
- Switcher is a session-only preference; it never mutates user.default_currency.
"""

from datetime import date, timedelta
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

# smart_money joins digit groups with U+2009 (THIN SPACE) and the apostrophe
# in "so'm" gets HTML-escaped to &#x27; when rendered into a template.
THIN = chr(0x2009)
SOM = "so&#x27;m"


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
    assert f"2{THIN}250{THIN}000 {SOM}" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_falls_back_to_raw_when_rates_missing() -> None:
    """No exchange rates → hero shows the user's default-currency total only."""
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
    # Hero falls back to UZS total (0). smart_money renders with "so'm" symbol.
    assert f"0 {SOM}" in body


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
    # 1_000_000 UZS / 12500 + 100 USD = 80 + 100 = 180 USD → "180 $"
    assert "180 $" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_renders_stale_banner_when_rates_old(monkeypatch) -> None:
    # home_content refreshes CBU rates on-demand when today's row is missing.
    # This test needs the seeded stale rates to stay stale, so stub the
    # refresh call to a no-op — otherwise a live network fetch inside the
    # test would insert today's rate and hide the banner.
    import core.views as _core_views

    monkeypatch.setattr(_core_views, "update_rates_if_stale", lambda **_kw: False)

    user = _seed_user_with_mixed_currencies()
    ExchangeRate.objects.all().delete()
    stale_date = date.today() - timedelta(days=30)
    ExchangeRate.objects.create(
        currency="USD",
        rate_to_uzs=Decimal("12500"),
        date=stale_date,
    )
    ExchangeRate.objects.create(
        currency="RUB",
        rate_to_uzs=Decimal("125"),
        date=stale_date,
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
def test_home_content_hero_reflects_cash_in_hand_including_debt_flow() -> None:
    """Sprint v0.8 final — hero shows CASH IN HAND, which includes debt
    movements. Borrowing 500k gives the user 500k more cash in their pocket
    (they'll have to give it back later — that shows as a Berishingiz kerak
    chip). The two views together = honest picture: I have 500k, I owe 500k.
    """
    user = User.objects.create(
        telegram_id=904,
        first_name="Borrower",
        onboarded_at=timezone.now(),
        default_currency="UZS",
    )
    TransactionFactory(
        user=user,
        type="debt_borrowed",
        amount=Decimal("500000"),
        currency="UZS",
        counterparty="Karim",
        date=date.today(),
    )
    client = Client()
    init_data = _make_init_data(user_id=user.telegram_id, first_name="Borrower")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    # Hero reflects the borrowed cash — user actually has 500k in pocket right now.
    assert "Sof balans" in body
    assert f"500{THIN}000 {SOM}" in body
    # And the outstanding liability shows as a Berishingiz kerak chip.
    assert "Berishingiz kerak" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_hero_drops_when_lending_out() -> None:
    """Eric's regression: 10M salary + 3M lent to Karim → hero must show
    7M (cash left the pocket) and the 3M surfaces as Olishingiz kerak.
    """
    user = User.objects.create(
        telegram_id=905,
        first_name="Lender",
        onboarded_at=timezone.now(),
        default_currency="UZS",
    )
    TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("10000000"),
        currency="UZS",
        date=date.today(),
    )
    TransactionFactory(
        user=user,
        type="debt_lent",
        amount=Decimal("3000000"),
        currency="UZS",
        counterparty="Karim",
        date=date.today(),
    )
    client = Client()
    init_data = _make_init_data(user_id=user.telegram_id, first_name="Lender")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    # Cash in hand = 10M income − 3M lent = 7M.
    assert f"7{THIN}000{THIN}000 {SOM}" in body
    # And Karim owes back 3M.
    assert "Olishingiz kerak" in body


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
