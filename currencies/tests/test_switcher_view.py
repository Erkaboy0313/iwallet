"""Story 5.5 — currency switcher view tests."""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.middleware import SESSION_KEY
from currencies.views import (
    DISPLAY_MODE_CONVERTED,
    DISPLAY_MODE_RAW,
    SESSION_DISPLAY_CURRENCY,
    SESSION_DISPLAY_MODE,
)
from transactions.tests.factories import UserFactory


@pytest.mark.django_db
def test_switch_display_persists_session_and_user() -> None:
    user = UserFactory(default_currency="UZS", show_converted=False)
    client = Client()
    session = client.session
    session[SESSION_KEY] = user.telegram_id
    session.save()

    response = client.post(
        reverse("currencies:switch_display"),
        data={"display_mode": "converted", "display_currency": "USD"},
    )
    assert response.status_code == 204
    # Must redirect to the full /app/home/ shell, not the partial /content/
    # endpoint — the partial is shell-less HTML and would render unstyled.
    assert response.headers["HX-Redirect"] == reverse("core:home")

    # Session updated.
    session = client.session
    assert session[SESSION_DISPLAY_CURRENCY] == "USD"
    assert session[SESSION_DISPLAY_MODE] == DISPLAY_MODE_CONVERTED

    user.refresh_from_db()
    assert user.show_converted is True
    assert user.default_currency == "USD"


@pytest.mark.django_db
def test_switch_display_raw_mode_persists() -> None:
    user = UserFactory(default_currency="UZS", show_converted=True)
    client = Client()
    session = client.session
    session[SESSION_KEY] = user.telegram_id
    session.save()

    response = client.post(
        reverse("currencies:switch_display"),
        data={"display_mode": "raw"},
    )
    assert response.status_code == 204
    user.refresh_from_db()
    assert user.show_converted is False
    session = client.session
    assert session[SESSION_DISPLAY_MODE] == DISPLAY_MODE_RAW


@pytest.mark.django_db
def test_switch_display_rejects_unknown_currency() -> None:
    user = UserFactory(default_currency="UZS")
    client = Client()
    session = client.session
    session[SESSION_KEY] = user.telegram_id
    session.save()

    response = client.post(
        reverse("currencies:switch_display"),
        data={"display_currency": "EUR", "display_mode": "converted"},
    )
    assert response.status_code == 204
    session = client.session
    assert SESSION_DISPLAY_CURRENCY not in session


@pytest.mark.django_db
def test_switch_display_requires_auth() -> None:
    """Anonymous (no session + no header) hits the protected /app/* perimeter."""
    client = Client()
    response = client.post(
        reverse("currencies:switch_display"),
        data={"display_mode": "converted", "display_currency": "USD"},
    )
    assert response.status_code == 401
