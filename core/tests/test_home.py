"""Story 1.5 — Home shell + auth'd BalanceHero content."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.middleware import SESSION_KEY
from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from transactions.tests.factories import TransactionFactory

# ---------- /app/home/ shell ----------


@pytest.mark.django_db
def test_healthz_anonymous_returns_ok() -> None:
    client = Client()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.content == b"ok"


@pytest.mark.django_db
def test_home_shell_renders_anonymously() -> None:
    """Shell is public — first GET has no initData."""
    client = Client()
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert 'hx-get="/app/home/content/"' in body
    assert "Yuklanmoqda" in body  # skeleton screen reader text


@pytest.mark.django_db
def test_home_shell_extends_base_layout() -> None:
    client = Client()
    response = client.get(reverse("core:home"))
    body = response.content.decode("utf-8")
    assert "telegram-web-app.js" in body
    assert 'aria-label="Uy"' in body


@pytest.mark.django_db
def test_home_renders_session_users_balance_without_another_request() -> None:
    user = User.objects.create(telegram_id=100, first_name="Owner", onboarded_at=timezone.now())
    TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("125000"),
        currency="UZS",
        date=timezone.localdate(),
    )
    TransactionFactory(
        type="income", amount=Decimal("987654321"), currency="UZS", date=timezone.localdate()
    )
    client = Client()
    session = client.session
    session[SESSION_KEY] = user.telegram_id
    session.save()

    response = client.get(reverse("core:home"))

    assert response.status_code == 200
    body = response.content.decode()
    assert "Sof balans" in body
    assert "125\u2009000" in body
    assert "987\u2009654\u2009321" not in body
    assert 'hx-get="/app/home/content/"' not in body
    assert "sessionid" not in response.cookies  # Reading a page need not write the session.


@pytest.mark.django_db
def test_home_with_deleted_session_user_still_renders_public_shell() -> None:
    client = Client()
    session = client.session
    session[SESSION_KEY] = 999999
    session.save()

    response = client.get(reverse("core:home"))

    assert response.status_code == 200
    assert 'hx-get="/app/home/content/"' in response.content.decode()


@pytest.mark.django_db
def test_home_never_waits_for_external_rates_when_database_has_none(monkeypatch) -> None:
    from currencies.models import ExchangeRate

    ExchangeRate.objects.all().delete()
    fetch = Mock(side_effect=AssertionError("Page rendering must not call CBU"))
    monkeypatch.setattr("currencies.services.fetch_cbu_rates", fetch)
    user = User.objects.create(telegram_id=101, onboarded_at=timezone.now())
    client = Client()
    session = client.session
    session[SESSION_KEY] = user.telegram_id
    session.save()

    for name in ("core:home", "core:home_content"):
        response = client.get(reverse(name))
        assert response.status_code == 200
        assert "Sof balans" in response.content.decode()
        assert "sessionid" not in response.cookies
    fetch.assert_not_called()


# ---------- /app/home/content/ (auth required) ----------


@pytest.mark.django_db
def test_home_content_returns_anonymous_fallback_when_init_data_missing() -> None:
    """Post-deploy fix: render a fallback card instead of 401 so users see something."""
    client = Client()
    response = client.get(reverse("core:home_content"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Telegram sizning identifikatoringizni uzatmadi" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_redirects_when_user_not_onboarded() -> None:
    client = Client()
    init_data = _make_init_data(user_id=7)
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == reverse("accounts:onboarding")


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_renders_balance_hero_when_onboarded() -> None:
    User.objects.create(telegram_id=8, first_name="Eric", onboarded_at=timezone.now())
    client = Client()
    init_data = _make_init_data(user_id=8, first_name="Eric")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Sprint v0.5 redesign — greeting removed (Phase 3 replaces with quote
    # card). Home now leads with Kirim / Chiqim cards above Sof balans.
    assert "Sof balans" in body
    assert "Kirim" in body
    assert "Chiqim" in body
    assert "0 so&#x27;m" in body or "0 so'm" in body  # empty user — zero balance
    assert "Birinchi tranzaksiyangizni qo'shing" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_content_shows_real_balance_for_onboarded_user() -> None:
    user = User.objects.create(telegram_id=9, first_name="Eric", onboarded_at=timezone.now())
    TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("1000000"),
        currency="UZS",
        date=date.today(),
    )
    TransactionFactory(
        user=user,
        type="expense",
        amount=Decimal("250000"),
        currency="UZS",
        date=date.today(),
    )

    client = Client()
    init_data = _make_init_data(user_id=9, first_name="Eric")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    # smart_money: 750000 → "750 000 so'm" (thin space + symbol).
    assert "750" in body
    assert "so&#x27;m" in body or "so'm" in body
