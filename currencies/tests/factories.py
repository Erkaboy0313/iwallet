"""factory-boy factories for currency models."""

from datetime import date as date_type
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from currencies.models import ExchangeRate


class ExchangeRateFactory(DjangoModelFactory):
    class Meta:
        model = ExchangeRate
        django_get_or_create = ("currency", "date")

    currency = "USD"
    rate_to_uzs = Decimal("12300.500000")
    date = factory.LazyFunction(date_type.today)
    source = "cbu.uz"
