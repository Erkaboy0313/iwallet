"""Read-side queries for the push queue (Epic 9).

All DB reads live here so views/services/management commands have a single
place to look. No writes, no side effects.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from django.db.models import QuerySet
from django.utils import timezone

from debts.models import ACTIVE_STATES, Debt

from .models import NotificationKind, PushQueueItem


def pending_pushes(*, limit: int = 100) -> QuerySet[PushQueueItem]:
    """Queue rows waiting for delivery, oldest first.

    `sent_at IS NULL` is the canonical "still owed". We rely on the existing
    `Index(["sent_at"])` from migration 0001 so the scan is cheap even once
    we've accumulated history (no separate `status` enum needed — `sent_at`
    is both flag and timestamp).
    """
    return (
        PushQueueItem.objects.filter(sent_at__isnull=True)
        .select_related("user")
        .order_by("created_at", "id")[:limit]
    )


def debts_due_on(on_date: date) -> QuerySet[Debt]:
    """Active debts whose `expected_return_date` falls on `on_date`.

    Used by the daily reminder enqueuer (Story 9.4). Uses the
    `(user, expected_return_date)` composite index reserved for this
    purpose in `debts.models.Debt.Meta`.
    """
    return (
        Debt.objects.filter(
            state__in=list(ACTIVE_STATES),
            expected_return_date=on_date,
        )
        .select_related("user")
        .order_by("user_id", "id")
    )


def already_queued_debt_due_ids(
    *,
    debt_ids: Iterable[int],
    since: int = 1,
) -> set[int]:
    """Return debt IDs that already have a pending or recently-sent push.

    `since` is days back: a debt enqueued yesterday for "today's" reminder
    shouldn't be re-enqueued. We treat any debt_due PushQueueItem created in
    the last `since` days as "covered", whether sent or not — Eric's bot is
    single-user so dedup window can stay aggressive.
    """
    cutoff = timezone.now() - timedelta(days=since)
    rows = PushQueueItem.objects.filter(
        kind=NotificationKind.DEBT_DUE.value,
        created_at__gte=cutoff,
        payload_json__debt_id__in=list(debt_ids),
    ).values_list("payload_json", flat=True)
    return {int(p["debt_id"]) for p in rows if isinstance(p, dict) and "debt_id" in p}
