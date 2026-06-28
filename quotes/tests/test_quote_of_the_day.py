"""Selector + dismiss flow tests for Sprint v0.5 Phase 3."""

from datetime import date

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from quotes.models import Quote, QuoteDismissal
from quotes.selectors import quote_of_the_day
from quotes.services import dismiss_forever, reenable


def _user(telegram_id: int) -> User:
    return User.objects.create(telegram_id=telegram_id, first_name="Eric")


@pytest.mark.django_db
def test_quote_of_the_day_returns_none_when_no_active_quotes() -> None:
    Quote.objects.all().delete()
    assert quote_of_the_day(_user(11)) is None


@pytest.mark.django_db
def test_quote_of_the_day_is_deterministic_within_day() -> None:
    user = _user(12)
    today = date(2026, 6, 28)
    first = quote_of_the_day(user, today=today)
    second = quote_of_the_day(user, today=today)
    assert first is not None
    assert first.id == second.id


@pytest.mark.django_db
def test_quote_of_the_day_varies_across_days() -> None:
    user = _user(13)
    a = quote_of_the_day(user, today=date(2026, 6, 28))
    # Walk forward up to 30 days; we expect at least one different pick.
    days_with_a_different_quote = sum(
        1 for d in range(1, 31) if quote_of_the_day(user, today=date(2026, 7, d)).id != a.id
    )
    assert days_with_a_different_quote > 0


@pytest.mark.django_db
def test_dismiss_forever_makes_selector_return_none() -> None:
    user = _user(14)
    assert quote_of_the_day(user) is not None
    dismiss_forever(user)
    assert quote_of_the_day(user) is None
    assert QuoteDismissal.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_reenable_clears_dismissal() -> None:
    user = _user(15)
    dismiss_forever(user)
    reenable(user)
    assert QuoteDismissal.objects.filter(user=user).count() == 0
    assert quote_of_the_day(user) is not None


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_hide_today_endpoint_sets_session_flag() -> None:
    _user(16)
    client = Client()
    response = client.post(
        reverse("quotes:hide_today"),
        headers={"X-Telegram-InitData": _make_init_data(user_id=16, first_name="Eric")},
    )
    assert response.status_code == 204
    assert client.session.get("iw_quote_hidden_today") is True


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_dismiss_endpoint_writes_db_row_and_session_flag() -> None:
    _user(17)
    client = Client()
    response = client.post(
        reverse("quotes:dismiss"),
        headers={"X-Telegram-InitData": _make_init_data(user_id=17, first_name="Eric")},
    )
    assert response.status_code == 204
    assert QuoteDismissal.objects.filter(user__telegram_id=17).count() == 1
    assert client.session.get("iw_quote_hidden_today") is True
