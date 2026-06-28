"""Story 8.4 — yearly view integration tests.

Covers the four branches the AC calls out (0 / 2 / 6 / 12 months of data) so
the partial-data hint and the "≥3 months" promotion both render correctly.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from transactions.tests.factories import TransactionFactory


def _user(telegram_id: int = 7) -> User:
    return User.objects.create(
        telegram_id=telegram_id, first_name="Eric", onboarded_at=timezone.now()
    )


@pytest.mark.django_db
def test_yearly_requires_auth() -> None:
    client = Client()
    response = client.get(reverse("reports:yearly"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_yearly_zero_months_shows_collecting_state() -> None:
    _user(830)
    client = Client()
    init = _make_init_data(user_id=830)

    response = client.get(
        reverse("reports:yearly"),
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Empty state hint specific to a fresh user.
    assert "Ma'lumot to'planmoqda" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_yearly_two_months_still_partial() -> None:
    user = _user(831)
    TransactionFactory(user=user, type="expense", amount=Decimal("100"), date=date(2026, 1, 5))
    TransactionFactory(user=user, type="expense", amount=Decimal("200"), date=date(2026, 2, 5))
    client = Client()
    init = _make_init_data(user_id=831)

    response = client.get(
        reverse("reports:yearly") + "?year=2026",
        headers={"X-Telegram-InitData": init},
    )
    body = response.content.decode("utf-8")
    assert "Ma'lumot to'planmoqda" in body
    # Partial bars still rendered.
    assert "<svg" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_yearly_six_months_renders_full_chart_with_highlight() -> None:
    user = _user(832)
    spends = {1: 100, 2: 200, 3: 150, 4: 9000, 5: 300, 6: 400}
    for m, amt in spends.items():
        TransactionFactory(user=user, type="expense", amount=Decimal(amt), date=date(2026, m, 5))
    client = Client()
    init = _make_init_data(user_id=832)

    response = client.get(
        reverse("reports:yearly") + "?year=2026",
        headers={"X-Telegram-InitData": init},
    )
    body = response.content.decode("utf-8")
    # No longer partial.
    assert "Ma'lumot to'planmoqda" not in body
    # Most-expensive callout points to April (Aprel).
    assert "Apr" in body
    # Amber highlight shade from the SVG bars helper.
    assert "#f59e0b" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_yearly_twelve_months_renders_complete_view() -> None:
    user = _user(833)
    for m in range(1, 13):
        TransactionFactory(
            user=user, type="expense", amount=Decimal(100 * m), date=date(2026, m, 5)
        )
    client = Client()
    init = _make_init_data(user_id=833)

    response = client.get(
        reverse("reports:yearly") + "?year=2026",
        headers={"X-Telegram-InitData": init},
    )
    body = response.content.decode("utf-8")
    # All 12 month labels should appear in the SVG.
    for short in [
        "Yan",
        "Fev",
        "Mar",
        "Apr",
        "May",
        "Iyn",
        "Iyl",
        "Avg",
        "Sen",
        "Okt",
        "Noy",
        "Dek",
    ]:
        assert short in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_yearly_yoy_comparison_renders_when_prev_year_has_data() -> None:
    user = _user(834)
    # 1000 last year, 2000 this year.
    TransactionFactory(user=user, type="expense", amount=Decimal("1000"), date=date(2025, 5, 5))
    TransactionFactory(user=user, type="expense", amount=Decimal("2000"), date=date(2026, 5, 5))
    client = Client()
    init = _make_init_data(user_id=834)

    response = client.get(
        reverse("reports:yearly") + "?year=2026",
        headers={"X-Telegram-InitData": init},
    )
    body = response.content.decode("utf-8")
    assert "O'tgan yilga nisbatan" in body
    # +100% delta — rendered as "100,0%" (uz locale uses comma decimal separator).
    assert "100,0%" in body or "100.0%" in body
    # Positive delta paints the pill amber.
    assert "yoy-delta" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_yearly_no_yoy_when_no_prior_year_data() -> None:
    user = _user(835)
    TransactionFactory(user=user, type="expense", amount=Decimal("1000"), date=date(2026, 1, 5))
    TransactionFactory(user=user, type="expense", amount=Decimal("2000"), date=date(2026, 2, 5))
    TransactionFactory(user=user, type="expense", amount=Decimal("3000"), date=date(2026, 3, 5))
    client = Client()
    init = _make_init_data(user_id=835)

    response = client.get(
        reverse("reports:yearly") + "?year=2026",
        headers={"X-Telegram-InitData": init},
    )
    body = response.content.decode("utf-8")
    # Section omitted entirely.
    assert "O'tgan yilga nisbatan" not in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_yearly_year_param_garbage_falls_back_to_current() -> None:
    _user(836)
    client = Client()
    init = _make_init_data(user_id=836)

    response = client.get(
        reverse("reports:yearly") + "?year=notayear",
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 200


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_yearly_prev_next_links_present() -> None:
    _user(837)
    client = Client()
    init = _make_init_data(user_id=837)

    response = client.get(
        reverse("reports:yearly") + "?year=2026",
        headers={"X-Telegram-InitData": init},
    )
    body = response.content.decode("utf-8")
    assert "year=2025" in body
    assert "year=2027" in body
