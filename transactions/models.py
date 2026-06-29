"""Transaction model + custom manager (Story 1.1).

Domain invariants — encoded as DB constraints + manager behavior, NOT view logic.
"""

from __future__ import annotations

from datetime import date as _date_type

from django.db import models

from accounts.models import User
from currencies.constants import CURRENCY_CHOICES

MAX_DIGITS = 15
DECIMAL_PLACES = 2


class TransactionType(models.TextChoices):
    INCOME = "income", "Kirim"
    EXPENSE = "expense", "Chiqim"
    DEBT_LENT = "debt_lent", "Qarz berdim"
    DEBT_BORROWED = "debt_borrowed", "Qarz oldim"


class TransactionQuerySet(models.QuerySet):
    """Composable read-side queries. Chain freely: `.for_user(u).in_period(s, e)`."""

    def for_user(self, user: User) -> TransactionQuerySet:
        """Owner scope + soft-deleted excluded (NFR11 row-level isolation)."""
        return self.filter(user=user, is_deleted=False)

    def in_period(self, start: _date_type, end: _date_type) -> TransactionQuerySet:
        """Inclusive date range [start, end]."""
        return self.filter(date__gte=start, date__lte=end)

    def by_type(self, type_: str) -> TransactionQuerySet:
        return self.filter(type=type_)


class TransactionManager(models.Manager.from_queryset(TransactionQuerySet)):
    """Default manager — proxies QuerySet methods so views/services can call them."""


class Transaction(models.Model):
    """A single money movement owned by one user.

    Storage rules (project-context.md):
      - amount is Decimal — never Float.
      - currency stored as ISO 4217 code; conversion is display-only.
      - Soft-delete via is_deleted + deleted_at (NOT hard delete in v1).
      - Indexes serve History (FR59), filters (FR60), and dashboards.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")

    type = models.CharField(max_length=16, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="UZS")
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    # counterparty is only meaningful for debt_lent / debt_borrowed; nullable otherwise.
    counterparty = models.CharField(max_length=64, blank=True, default="")
    date = models.DateField()
    note = models.TextField(blank=True, default="")

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Set when a debt-type transaction has been settled (the counterparty has
    # been paid back, or the user has paid them back). Null on regular income
    # / expense rows and on still-open debts. The settle action also spawns a
    # paired income/expense Transaction so the cash flow stays correct.
    settled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TransactionManager()

    class Meta:
        db_table = "transactions_transaction"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "type", "date"]),
            models.Index(fields=["user", "is_deleted"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="transactions_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.type} {self.amount} {self.currency} @ {self.date}"
