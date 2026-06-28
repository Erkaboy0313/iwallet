"""Story 5.4 — `convert_for_display` + stale fallback + selectors tests."""

from datetime import date
from decimal import Decimal

import pytest

from currencies.exceptions import MissingRateError
from currencies.models import ExchangeRate
from currencies.selectors import current_rates_stale_days, latest_rate
from currencies.services import convert_for_display, safe_convert_for_display


def _seed(currency: str, rate: str, on: date) -> ExchangeRate:
    return ExchangeRate.objects.create(
        currency=currency,
        rate_to_uzs=Decimal(rate),
        date=on,
    )


@pytest.mark.django_db
def test_uzs_to_uzs_is_noop() -> None:
    result = convert_for_display(Decimal("100000"), "UZS", "UZS")
    assert result.amount == Decimal("100000.00")
    assert result.converted is False
    assert result.is_stale is False


@pytest.mark.django_db
def test_usd_to_uzs_uses_today_rate() -> None:
    today = date(2026, 6, 28)
    _seed("USD", "12345.67", today)
    result = convert_for_display(Decimal("100"), "USD", "UZS", as_of_date=today)
    assert result.amount == Decimal("1234567.00")
    assert result.is_stale is False
    assert result.rate_date == today
    assert result.converted is True


@pytest.mark.django_db
def test_uzs_to_usd_divides_by_rate() -> None:
    today = date(2026, 6, 28)
    _seed("USD", "12500.00", today)
    result = convert_for_display(Decimal("1250000"), "UZS", "USD", as_of_date=today)
    assert result.amount == Decimal("100.00")


@pytest.mark.django_db
def test_usd_to_rub_pivots_through_uzs() -> None:
    today = date(2026, 6, 28)
    _seed("USD", "12500.00", today)
    _seed("RUB", "125.00", today)
    # 1 USD = 12500 UZS = 100 RUB
    result = convert_for_display(Decimal("2"), "USD", "RUB", as_of_date=today)
    assert result.amount == Decimal("200.00")
    assert result.converted is True
    assert result.is_stale is False


@pytest.mark.django_db
def test_stale_rate_flagged_when_no_today_row() -> None:
    today = date(2026, 6, 28)
    yesterday = date(2026, 6, 27)
    _seed("USD", "12345.67", yesterday)
    result = convert_for_display(Decimal("100"), "USD", "UZS", as_of_date=today)
    assert result.is_stale is True
    assert result.rate_date == yesterday
    assert result.amount == Decimal("1234567.00")


@pytest.mark.django_db
def test_missing_rate_raises_when_not_bootstrapped() -> None:
    with pytest.raises(MissingRateError):
        convert_for_display(Decimal("100"), "USD", "UZS", as_of_date=date(2026, 6, 28))


@pytest.mark.django_db
def test_safe_convert_returns_none_when_missing() -> None:
    result = safe_convert_for_display(Decimal("100"), "USD", "UZS")
    assert result is None


@pytest.mark.django_db
def test_safe_convert_returns_result_when_present() -> None:
    today = date(2026, 6, 28)
    _seed("USD", "12345.67", today)
    result = safe_convert_for_display(Decimal("100"), "USD", "UZS", as_of_date=today)
    assert result is not None
    assert result.amount == Decimal("1234567.00")


@pytest.mark.django_db
def test_amount_accepts_string_or_int() -> None:
    today = date(2026, 6, 28)
    _seed("USD", "12345.67", today)
    s = convert_for_display("100", "USD", "UZS", as_of_date=today)
    i = convert_for_display(100, "USD", "UZS", as_of_date=today)
    assert s.amount == i.amount == Decimal("1234567.00")


@pytest.mark.django_db
def test_lowercase_currency_codes_accepted() -> None:
    today = date(2026, 6, 28)
    _seed("USD", "12500.00", today)
    result = convert_for_display(Decimal("1250000"), "uzs", "usd", as_of_date=today)
    assert result.amount == Decimal("100.00")


@pytest.mark.django_db
def test_current_rates_stale_days_returns_minus_one_when_empty() -> None:
    assert current_rates_stale_days(today=date(2026, 6, 28)) == -1


@pytest.mark.django_db
def test_current_rates_stale_days_returns_zero_when_today_present() -> None:
    today = date(2026, 6, 28)
    _seed("USD", "12345.67", today)
    assert current_rates_stale_days(today=today) == 0


@pytest.mark.django_db
def test_current_rates_stale_days_returns_positive_when_old() -> None:
    today = date(2026, 6, 28)
    _seed("USD", "12345.67", date(2026, 6, 25))
    assert current_rates_stale_days(today=today) == 3


@pytest.mark.django_db
def test_latest_rate_uzs_is_identity_and_never_stale() -> None:
    look = latest_rate("UZS", on_or_before=date(2026, 6, 28))
    assert look is not None
    assert look.rate_to_uzs == Decimal("1")
    assert look.is_stale is False
