"""RecurringSchedule model (Epic 7 / Story 7.1).

A schedule tells the daily tick which Transaction to materialize on which day.
The schema mirrors `transactions.Transaction` (same currency, category, amount
shape) so the dispatcher can hand fields straight to
`transactions.services.create_transaction` without conversion.

Cadence model (project-context.md):
  - `monthly` + day_of_month (1..31) — Feb 30 collapses to Feb 28/29.
  - `weekly` + day_of_week (0=Mon..6=Sun, Python ISO).

`next_dispatch_at` is denormalized so we can index a single column for the
tick query instead of recomputing per row. The tick service is the only writer
of this field — services own the invariant.
"""

from __future__ import annotations

from django.db import models

from accounts.models import User
from currencies.constants import CURRENCY_CHOICES

MAX_DIGITS = 15
DECIMAL_PLACES = 2


class RecurringType(models.TextChoices):
    INCOME = "income", "Kirim"
    EXPENSE = "expense", "Chiqim"
    DEBT_LENT = "debt_lent", "Qarz berdim"
    DEBT_BORROWED = "debt_borrowed", "Qarz oldim"


class ScheduleKind(models.TextChoices):
    DAILY = "daily", "Har kuni"
    WEEKLY = "weekly", "Haftalik"
    MONTHLY = "monthly", "Oylik"


class RecurringScheduleQuerySet(models.QuerySet):
    """Composable read-side queries for the settings + home prompt views."""

    def for_user(self, user: User) -> RecurringScheduleQuerySet:
        return self.filter(user=user)

    def active(self) -> RecurringScheduleQuerySet:
        return self.filter(is_active=True)


class RecurringScheduleManager(models.Manager.from_queryset(RecurringScheduleQuerySet)):
    """Default manager — proxies QuerySet methods so views/services can call them."""


class RecurringSchedule(models.Model):
    """A user-defined cadence that emits Transactions on each tick.

    Per AC 7.1 the model stores the *intent* (kind + day_*), the *template*
    (type, amount, currency, category, name), and *bookkeeping*
    (next_dispatch_at, last_dispatched_on, is_active).
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recurring_schedules",
    )

    type = models.CharField(max_length=16, choices=RecurringType.choices)
    name = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="UZS")
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_schedules",
    )

    schedule_kind = models.CharField(max_length=8, choices=ScheduleKind.choices)
    day_of_month = models.PositiveSmallIntegerField(null=True, blank=True)  # 1..31
    day_of_week = models.PositiveSmallIntegerField(null=True, blank=True)  # 0..6 (Mon..Sun)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    next_dispatch_at = models.DateField()
    last_dispatched_on = models.DateField(
        null=True,
        blank=True,
        help_text="Date the last Transaction was materialized (idempotency key).",
    )
    defer_until = models.DateField(
        null=True,
        blank=True,
        help_text="If set, the prompt is hidden from the home page until this date.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RecurringScheduleManager()

    class Meta:
        db_table = "recurring_schedule"
        ordering = ["-is_active", "next_dispatch_at", "name"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["is_active", "next_dispatch_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="recurring_amount_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(schedule_kind="monthly", day_of_month__gte=1, day_of_month__lte=31)
                    | models.Q(schedule_kind="weekly", day_of_week__gte=0, day_of_week__lte=6)
                    | models.Q(schedule_kind="daily")
                ),
                name="recurring_schedule_cadence_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.schedule_kind}) → {self.next_dispatch_at}"
