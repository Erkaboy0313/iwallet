"""Story 1.0 — First-Run Onboarding tests."""

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.services import mark_onboarded
from accounts.tests.test_services import BOT_TOKEN, _make_init_data

# ---------- mark_onboarded service ----------


@pytest.mark.django_db
def test_mark_onboarded_sets_timestamp() -> None:
    user = User.objects.create(telegram_id=42, first_name="Eric")
    assert user.onboarded_at is None

    mark_onboarded(user)
    user.refresh_from_db()
    assert user.onboarded_at is not None
    assert (timezone.now() - user.onboarded_at).total_seconds() < 5


@pytest.mark.django_db
def test_mark_onboarded_idempotent_does_not_overwrite() -> None:
    """Calling mark_onboarded twice keeps the original timestamp (no overwrite)."""
    user = User.objects.create(telegram_id=42, first_name="Eric")
    mark_onboarded(user)
    user.refresh_from_db()
    first_ts = user.onboarded_at

    mark_onboarded(user)
    user.refresh_from_db()
    assert user.onboarded_at == first_ts


# ---------- onboarding_view (public) ----------


@pytest.mark.django_db
def test_onboarding_view_renders_anonymously() -> None:
    """/app/onboarding/ is a public shell — anonymous GET returns 200 with the 3 cards."""
    client = Client()
    response = client.get(reverse("accounts:onboarding"))
    assert response.status_code == 200

    body = response.content.decode("utf-8")
    # 3 cards present (verify by card heading text)
    assert "10 soniyada" in body  # Card 1 heading fragment
    assert "4 ta tranzaksiya turi" in body  # Card 2 heading
    assert "Voice yoki qo'lda" in body  # Card 3 heading
    # CTA + skip
    assert "Boshlash" in body
    assert "O'tkazib yuborish" in body


@pytest.mark.django_db
def test_onboarding_view_extends_base_layout() -> None:
    client = Client()
    response = client.get(reverse("accounts:onboarding"))
    body = response.content.decode("utf-8")
    assert "telegram-web-app.js" in body
    assert "width=device-width" in body


# ---------- onboarding_complete_view (auth required) ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_complete_view_marks_user_onboarded_with_valid_init_data() -> None:
    client = Client()
    init_data = _make_init_data(user_id=99, first_name="Eric")
    response = client.post(
        reverse("accounts:onboarding_complete"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    # HX-Redirect header drives the client-side navigation
    assert response.headers.get("HX-Redirect") == reverse("core:home")

    user = User.objects.get(telegram_id=99)
    assert user.onboarded_at is not None


@pytest.mark.django_db
def test_complete_view_returns_401_without_init_data() -> None:
    """Completion endpoint is auth-required (not in PUBLIC_APP_PATHS)."""
    client = Client()
    response = client.post(reverse("accounts:onboarding_complete"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_complete_view_only_accepts_post() -> None:
    client = Client()
    init_data = _make_init_data(user_id=99)
    response = client.get(
        reverse("accounts:onboarding_complete"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 405  # Method not allowed
