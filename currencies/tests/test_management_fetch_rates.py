"""Story 5.3 — `python manage.py fetch_rates` integration tests."""

from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from currencies.exceptions import CbuUnavailableError
from currencies.models import ExchangeRate


@pytest.mark.django_db
def test_fetch_rates_creates_rows() -> None:
    today = date.today()
    payload = {"USD": Decimal("12345.67"), "RUB": Decimal("134.56"), "date": today}
    with patch("currencies.services.fetch_cbu_rates", return_value=payload):
        buf = StringIO()
        call_command("fetch_rates", stdout=buf)
    assert ExchangeRate.objects.filter(date=today).count() == 2
    assert "Rates checked/refreshed" in buf.getvalue()


@pytest.mark.django_db
def test_fetch_rates_noop_when_today_cached() -> None:
    today = date.today()
    ExchangeRate.objects.create(currency="USD", rate_to_uzs=Decimal("12000"), date=today)
    with patch("currencies.services.fetch_cbu_rates") as fake:
        buf = StringIO()
        call_command("fetch_rates", stdout=buf)
    fake.assert_not_called()
    assert "no-op" in buf.getvalue()


@pytest.mark.django_db
def test_force_flag_overwrites_existing_rates() -> None:
    today = date.today()
    ExchangeRate.objects.create(currency="USD", rate_to_uzs=Decimal("11000"), date=today)
    payload = {"USD": Decimal("12500.00"), "RUB": Decimal("130.00"), "date": today}
    with (
        patch("currencies.cbu_client.fetch_cbu_rates", return_value=payload),
        patch(
            "currencies.management.commands.fetch_rates.fetch_cbu_rates",
            return_value=payload,
        ),
    ):
        buf = StringIO()
        call_command("fetch_rates", "--force", stdout=buf)
    usd = ExchangeRate.objects.get(currency="USD", date=today)
    assert usd.rate_to_uzs == Decimal("12500.000000")
    assert "Force-fetched" in buf.getvalue()


@pytest.mark.django_db
def test_force_flag_warns_when_cbu_down() -> None:
    with patch(
        "currencies.management.commands.fetch_rates.fetch_cbu_rates",
        side_effect=CbuUnavailableError("down"),
    ):
        out = StringIO()
        err = StringIO()
        call_command("fetch_rates", "--force", stdout=out, stderr=err)
    assert "CBU.uz unreachable" in err.getvalue()
    assert ExchangeRate.objects.count() == 0
