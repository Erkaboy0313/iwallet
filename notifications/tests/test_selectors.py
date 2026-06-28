"""Story 9.3/9.4 — selectors are pure read-side; pin their queryset shape."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from debts.models import DebtState
from debts.tests.factories import DebtFactory
from notifications.models import NotificationKind, PushQueueItem
from notifications.selectors import (
    already_queued_debt_due_ids,
    debts_due_on,
    pending_pushes,
)
from transactions.tests.factories import UserFactory


@pytest.mark.django_db(transaction=True)
def test_pending_pushes_only_returns_unsent_oldest_first() -> None:
    user = UserFactory(telegram_id=2001)
    sent = PushQueueItem.objects.create(
        user=user,
        kind=NotificationKind.RECURRING_FIRED.value,
        payload_json={"x": 1},
        sent_at=timezone.now(),
    )
    a = PushQueueItem.objects.create(
        user=user,
        kind=NotificationKind.RECURRING_FIRED.value,
        payload_json={"x": 2},
    )
    b = PushQueueItem.objects.create(
        user=user,
        kind=NotificationKind.RECURRING_FIRED.value,
        payload_json={"x": 3},
    )
    rows = list(pending_pushes())
    ids = [r.id for r in rows]
    assert sent.id not in ids
    assert ids == [a.id, b.id]  # oldest first


@pytest.mark.django_db(transaction=True)
def test_pending_pushes_respects_limit() -> None:
    user = UserFactory(telegram_id=2002)
    for i in range(5):
        PushQueueItem.objects.create(
            user=user,
            kind=NotificationKind.RECURRING_FIRED.value,
            payload_json={"i": i},
        )
    assert len(list(pending_pushes(limit=2))) == 2


@pytest.mark.django_db(transaction=True)
def test_debts_due_on_filters_by_date_and_state() -> None:
    user = UserFactory(telegram_id=2003)
    today = date(2026, 7, 15)
    DebtFactory(user=user, expected_return_date=today)
    DebtFactory(user=user, expected_return_date=today, state=DebtState.PARTIAL.value)
    DebtFactory(user=user, expected_return_date=today + timedelta(days=1))  # wrong date
    DebtFactory(user=user, expected_return_date=today, state=DebtState.CLOSED.value)  # closed
    DebtFactory(user=user, expected_return_date=None)  # no date set

    rows = list(debts_due_on(today))
    assert len(rows) == 2


@pytest.mark.django_db(transaction=True)
def test_already_queued_debt_due_ids_returns_recent_dedupe_set() -> None:
    user = UserFactory(telegram_id=2004)
    debt1 = DebtFactory(user=user, expected_return_date=date.today())
    debt2 = DebtFactory(user=user, expected_return_date=date.today())
    PushQueueItem.objects.create(
        user=user,
        kind=NotificationKind.DEBT_DUE.value,
        payload_json={"debt_id": debt1.id},
    )
    seen = already_queued_debt_due_ids(debt_ids=[debt1.id, debt2.id])
    assert seen == {debt1.id}
