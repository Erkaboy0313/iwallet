"""factory-boy factories for PushQueueItem."""

from __future__ import annotations

import factory
from factory.django import DjangoModelFactory

from notifications.models import NotificationKind, PushQueueItem
from transactions.tests.factories import UserFactory


class PushQueueItemFactory(DjangoModelFactory):
    class Meta:
        model = PushQueueItem

    user = factory.SubFactory(UserFactory)
    kind = NotificationKind.RECURRING_FIRED.value
    payload_json = factory.LazyFunction(
        lambda: {
            "schedule_id": 1,
            "schedule_name": "Ijara",
            "transaction_id": 1,
            "amount": "100000.00",
            "currency": "UZS",
            "fired_on": "2026-07-01",
        }
    )
    sent_at = None
