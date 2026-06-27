"""factory-boy factories for Transaction-related models."""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from accounts.models import User
from transactions.models import Transaction


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("telegram_id",)

    telegram_id = factory.Sequence(lambda n: 10000 + n)
    first_name = factory.Faker("first_name")
    username = factory.LazyAttribute(lambda o: o.first_name.lower())


class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = Transaction

    user = factory.SubFactory(UserFactory)
    type = "expense"
    amount = Decimal("10000.00")
    currency = "UZS"
    date = factory.Faker("date_object")
    note = ""
