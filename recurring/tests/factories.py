"""factory-boy factories for RecurringSchedule (Epic 7)."""

from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from recurring.models import RecurringSchedule
from transactions.tests.factories import UserFactory


class RecurringScheduleFactory(DjangoModelFactory):
    class Meta:
        model = RecurringSchedule

    user = factory.SubFactory(UserFactory)
    type = "expense"
    name = factory.Sequence(lambda n: f"Rule {n}")
    amount = Decimal("100000.00")
    currency = "UZS"
    schedule_kind = "monthly"
    day_of_month = 1
    day_of_week = None
    start_date = date(2026, 1, 1)
    end_date = None
    next_dispatch_at = date(2026, 2, 1)
    is_active = True
