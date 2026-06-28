"""Read-side queries for RecurringSchedule (Epic 7).

Views call into here so no Django ORM leaks into view modules
(project-context: services/selectors own DB access).
"""

from __future__ import annotations

from datetime import date

from django.db.models import QuerySet

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


def due_today(on_date: date) -> QuerySet[RecurringSchedule]:
    """Active schedules due on or before `on_date` — used by the tick command."""
    return RecurringSchedule.objects.due_on(on_date).select_related("user", "category")
