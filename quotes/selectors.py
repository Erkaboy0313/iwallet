"""Read-side helpers for the daily quote (Sprint v0.5 Phase 3)."""

from __future__ import annotations

from datetime import date as _date

from django.utils import timezone

from accounts.models import User

from .models import Quote, QuoteDismissal


def quote_of_the_day(user: User, *, today: _date | None = None) -> Quote | None:
    """Return today's quote for `user`, or None if disabled/empty.

    Deterministic per (user, day): the same telegram_id will see the same
    quote at every refresh today, and tomorrow's quote will be different.
    Falls through to None whenever the user has dismissed the feature OR
    there are no active quotes seeded.
    """
    today = today or timezone.localdate()
    if QuoteDismissal.objects.filter(user=user).exists():
        return None
    active_ids = list(Quote.objects.filter(is_active=True).values_list("id", flat=True))
    if not active_ids:
        return None
    seed = hash((int(user.telegram_id), today.isoformat()))
    return Quote.objects.get(pk=active_ids[seed % len(active_ids)])
