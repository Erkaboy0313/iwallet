"""Sprint 0 — Story 0.9 — Home view + auth smoke test."""

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_healthz_anonymous_returns_ok() -> None:
    """Healthcheck endpoint is anonymous (no auth header) — returns 200 'ok'."""
    client = Client()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.content == b"ok"


@pytest.mark.django_db
def test_home_returns_200_anonymous_shell() -> None:
    """/app/home/ is a public shell (PUBLIC_APP_PATHS) — anonymous GET returns 200.

    Per-user data is fetched client-side via Telegram WebApp SDK + future htmx
    auth'd endpoints; the initial page render does not require initData.
    """
    client = Client()
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    # Placeholder fallback name renders server-side; JS overrides with real
    # Telegram user when WebApp is opened.
    assert b'id="user-first-name"' in response.content


@pytest.mark.django_db
def test_home_renders_base_layout_chrome() -> None:
    """Home extends base.html — viewport, bottom nav, Telegram SDK script all present."""
    client = Client()
    response = client.get(reverse("core:home"))
    body = response.content.decode("utf-8")
    assert "width=device-width" in body
    assert "telegram-web-app.js" in body
    assert 'aria-label="Uy"' in body  # bottom nav present
    assert "initDataUnsafe" in body  # JS reads user name client-side
