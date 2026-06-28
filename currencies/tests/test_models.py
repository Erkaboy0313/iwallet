"""Story 5.2 — ExchangeRate model invariants."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from currencies.models import ExchangeRate


@pytest.mark.django_db
def test_unique_currency_date() -> None:
    ExchangeRate.objects.create(
        currency="USD",
        rate_to_uzs=Decimal("12000.000000"),
        date=date(2026, 6, 28),
    )
    with pytest.raises(IntegrityError):
        ExchangeRate.objects.create(
            currency="USD",
            rate_to_uzs=Decimal("12100.000000"),
            date=date(2026, 6, 28),
        )


@pytest.mark.django_db
def test_rate_must_be_positive() -> None:
    with pytest.raises(IntegrityError):
        ExchangeRate.objects.create(
            currency="USD",
            rate_to_uzs=Decimal("0"),
            date=date(2026, 6, 28),
        )


@pytest.mark.django_db
def test_str_representation_includes_pair() -> None:
    row = ExchangeRate.objects.create(
        currency="USD",
        rate_to_uzs=Decimal("12345.670000"),
        date=date(2026, 6, 28),
    )
    rendered = str(row)
    assert "USD" in rendered
    assert "12345.67" in rendered
    assert "2026-06-28" in rendered
