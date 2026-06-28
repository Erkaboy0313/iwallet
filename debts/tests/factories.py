"""factory-boy factories for Debt-related models."""

from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from debts.models import Debt, DebtRepayment, DebtState
from transactions.tests.factories import UserFactory


class DebtFactory(DjangoModelFactory):
    class Meta:
        model = Debt

    user = factory.SubFactory(UserFactory)
    direction = "lent"
    counterparty = factory.Sequence(lambda n: f"Counterparty {n}")
    original_amount = Decimal("100000.00")
    remaining_amount = Decimal("100000.00")
    currency = "UZS"
    state = DebtState.OPEN.value


class DebtRepaymentFactory(DjangoModelFactory):
    class Meta:
        model = DebtRepayment

    debt = factory.SubFactory(DebtFactory)
    amount = Decimal("10000.00")
    repaid_at = factory.LazyFunction(timezone.now)
