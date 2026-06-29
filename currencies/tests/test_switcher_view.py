"""Currency switcher view tests — v0.7 simplified model.

Switcher only flips the session-scoped balance-display currency.
It no longer touches user.default_currency or any "mode" flag —
those concepts were removed when we collapsed the dual raw/converted
modes into a single always-aggregated balance hero.
"""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.middleware import SESSION_KEY
from currencies.views import SESSION_DISPLAY_CURRENCY
from transactions.tests.factories import UserFactory


@pytest.mark.django_db
def test_switch_display_persists_session_currency() -> None:
    user = UserFactory(default_currency="UZS")
    client = Client()
    session = client.session
    session[SESSION_KEY] = user.telegram_id
    session.save()

    response = client.post(
        reverse("currencies:switch_display"),
        data={"display_currency": "USD"},
    )
    assert response.status_code == 204
    # Must redirect to the full /app/home/ shell, not the partial /content/
    # endpoint — the partial is shell-less HTML and would render unstyled.
    assert response.headers["HX-Redirect"] == reverse("core:home")

    # Session updated; user.default_currency intentionally NOT touched.
    session = client.session
    assert session[SESSION_DISPLAY_CURRENCY] == "USD"
    user.refresh_from_db()
    assert user.default_currency == "UZS"


@pytest.mark.django_db
def test_switch_display_rejects_unknown_currency() -> None:
    user = UserFactory(default_currency="UZS")
    client = Client()
    session = client.session
    session[SESSION_KEY] = user.telegram_id
    session.save()

    response = client.post(
        reverse("currencies:switch_display"),
        data={"display_currency": "EUR"},
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
        data={"display_currency": "USD"},
    )
    assert response.status_code == 401
