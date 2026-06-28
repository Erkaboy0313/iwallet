"""Story 5.2 — `store_rates` + `update_rates_if_stale` tests."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from currencies.exceptions import CbuUnavailableError
from currencies.models import ExchangeRate
from currencies.services import store_rates, update_rates_if_stale


@pytest.mark.django_db
def test_store_rates_creates_rows() -> None:
    saved = store_rates(
        on_date=date(2026, 6, 28),
        rates={"USD": Decimal("12345.67"), "RUB": Decimal("134.56")},
    )
    assert len(saved) == 2
    assert ExchangeRate.objects.count() == 2
    usd = ExchangeRate.objects.get(currency="USD", date=date(2026, 6, 28))
    assert usd.rate_to_uzs == Decimal("12345.670000")


@pytest.mark.django_db
def test_store_rates_is_idempotent() -> None:
    store_rates(on_date=date(2026, 6, 28), rates={"USD": Decimal("12000")})
    store_rates(on_date=date(2026, 6, 28), rates={"USD": Decimal("12500")})
    assert ExchangeRate.objects.count() == 1
    usd = ExchangeRate.objects.get(currency="USD", date=date(2026, 6, 28))
    # update_or_create updates the value.
    assert usd.rate_to_uzs == Decimal("12500.000000")


@pytest.mark.django_db
def test_store_rates_ignores_non_currency_keys() -> None:
    # Caller may pass the raw CBU dict with a 'date' key — that's fine.
    saved = store_rates(
        on_date=date(2026, 6, 28),
        rates={"USD": Decimal("1"), "date": date(2026, 6, 28)},  # type: ignore[dict-item]
    )
    assert len(saved) == 1


@pytest.mark.django_db
def test_update_rates_if_stale_skips_when_today_present() -> None:
    today = date(2026, 6, 28)
    ExchangeRate.objects.create(currency="USD", rate_to_uzs=Decimal("12000"), date=today)
    with patch("currencies.services.fetch_cbu_rates") as fake_fetch:
        called = update_rates_if_stale(today=today)
    assert called is False
    fake_fetch.assert_not_called()


@pytest.mark.django_db
def test_update_rates_if_stale_fetches_and_stores() -> None:
    today = date(2026, 6, 28)
    payload = {"USD": Decimal("12345.67"), "RUB": Decimal("134.56"), "date": today}
    with patch("currencies.services.fetch_cbu_rates", return_value=payload):
        called = update_rates_if_stale(today=today)
    assert called is True
    assert ExchangeRate.objects.filter(date=today).count() == 2


@pytest.mark.django_db
def test_update_rates_if_stale_swallows_cbu_outage() -> None:
    today = date(2026, 6, 28)
    with patch(
        "currencies.services.fetch_cbu_rates",
        side_effect=CbuUnavailableError("down"),
    ):
        called = update_rates_if_stale(today=today)
    # We DID attempt to fetch — the return is True, but no rows were stored.
    assert called is True
    assert ExchangeRate.objects.count() == 0
