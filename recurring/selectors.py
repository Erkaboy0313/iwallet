"""Read-side queries for RecurringSchedule (Epic 7).

Views call into here so no Django ORM leaks into view modules
(project-context: services/selectors own DB access).
"""

from __future__ import annotations

from datetime import date

from django.db.models import F, Q, QuerySet

from accounts.models import User

from .models import RecurringSchedule


def schedules_for(user: User) -> QuerySet[RecurringSchedule]:
    """All of `user`'s recurring schedules, active first, then by next fire."""
    return (
        RecurringSchedule.objects.for_user(user)
        .select_related("category")
        .order_by("-is_active", "next_dispatch_at", "name")
    )


def active_count_for(user: User) -> int:
    return RecurringSchedule.objects.for_user(user).active().count()


def pending_prompts(user: User, *, today: date) -> QuerySet[RecurringSchedule]:
    """Active schedules whose next fire is today-or-past and not deferred past today.

    These are surfaced as 'Bugun [name] qo'shamizmi?' prompts on home. End-dated
    schedules whose next fire would land past their end are filtered out (the
    schedule has run its course).
    """
    return (
        RecurringSchedule.objects.for_user(user)
        .active()
        .filter(next_dispatch_at__lte=today)
        .filter(Q(defer_until__isnull=True) | Q(defer_until__lte=today))
        .filter(Q(end_date__isnull=True) | Q(next_dispatch_at__lte=F("end_date")))
        .select_related("category")
        .order_by("next_dispatch_at", "id")
    )
