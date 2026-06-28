"""Sprint v0.5 Phase 4 — Settings hub at /app/settings/."""

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from quotes.models import QuoteDismissal


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_settings_hub_renders_for_onboarded_user() -> None:
    User.objects.create(telegram_id=201, first_name="Eric", onboarded_at=timezone.now())
    client = Client()
    init_data = _make_init_data(user_id=201, first_name="Eric")
    response = client.get(
        reverse("core:settings_hub"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # All four sections present.
    assert "Profil" in body
    assert "Pul" in body
    assert "Tartib" in body
    assert "Maxfiylik" in body
    # Sub-links visible.
    assert reverse("categories:list") in body
    assert reverse("recurring:list") in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_toggle_quote_feature_dismisses_when_enabled_is_zero() -> None:
    User.objects.create(telegram_id=202, first_name="Eric", onboarded_at=timezone.now())
    client = Client()
    init_data = _make_init_data(user_id=202, first_name="Eric")
    response = client.post(
        reverse("core:toggle_quote_feature"),
        data={"enabled": "0"},
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == reverse("core:settings_hub")
    assert QuoteDismissal.objects.filter(user__telegram_id=202).count() == 1


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_toggle_quote_feature_reenables_when_enabled_is_one() -> None:
    user = User.objects.create(telegram_id=203, first_name="Eric", onboarded_at=timezone.now())
    QuoteDismissal.objects.create(user=user)
    client = Client()
    init_data = _make_init_data(user_id=203, first_name="Eric")
    response = client.post(
        reverse("core:toggle_quote_feature"),
        data={"enabled": "1"},
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    assert QuoteDismissal.objects.filter(user=user).count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_balance_hero_links_to_settings_hub_via_gear_icon() -> None:
    User.objects.create(telegram_id=204, first_name="Eric", onboarded_at=timezone.now())
    client = Client()
    init_data = _make_init_data(user_id=204, first_name="Eric")
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    assert reverse("core:settings_hub") in body
    assert "Sozlamalar" in body  # aria-label
