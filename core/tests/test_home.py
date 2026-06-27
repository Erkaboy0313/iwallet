"""Sprint 0 — Story 0.9 — Home view + auth smoke test."""

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from accounts.tests.test_services import BOT_TOKEN, _make_init_data


@pytest.mark.django_db
def test_healthz_anonymous_returns_ok() -> None:
    """Healthcheck endpoint is anonymous (no auth header) — returns 200 'ok'."""
    client = Client()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.content == b"ok"


@pytest.mark.django_db
def test_home_returns_401_without_init_data() -> None:
    """Unauthenticated /app/home/ → 401 via TelegramAuthMiddleware."""
    client = Client()
    response = client.get(reverse("core:home"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_returns_200_with_valid_init_data() -> None:
    """Valid initData → Home rendered with the user's first name."""
    client = Client()
    init_data = _make_init_data(user_id=999, first_name="Eric", username="eric")
    response = client.get(
        reverse("core:home"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    assert b"Salom, Eric" in response.content


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_renders_base_layout_chrome() -> None:
    """Home extends base.html — viewport, bottom nav, Telegram SDK script all present."""
    client = Client()
    init_data = _make_init_data(user_id=1)
    response = client.get(
        reverse("core:home"),
        headers={"X-Telegram-InitData": init_data},
    )
    body = response.content.decode("utf-8")
    assert "width=device-width" in body
    assert "telegram-web-app.js" in body
    assert 'aria-label="Uy"' in body  # bottom nav present
