"""Debt + DebtRepayment models (Story 4.1).

A `Debt` is the long-lived aggregate the user sees in the UI: "Karim — 100 000
UZS qoldi". Each partial repayment lives as a :class:`DebtRepayment` row so the
timeline view (Story 4.4) can show the full history without losing the rolled-up
remaining amount.

Storage rules (project-context.md):
  - amount fields are Decimal — never Float.
  - currency is stored as ISO 4217 code; conversion is display-only.
  - state changes go through `debts.services` / `debts.state_machine` — the
    model itself only enforces constraints (positive amounts, ranges).
  - Indexes serve the two-tab debts screen (FR/UX-DR8 — Story 4.3).
"""

from __future__ import annotations

from django.db import models

from accounts.models import CURRENCY_CHOICES, User

MAX_DIGITS = 15
DECIMAL_PLACES = 2


class DebtDirection(models.TextChoices):
    LENT = "lent", "Men berdim"  # other person owes me
    BORROWED = "borrowed", "Men oldim"  # I owe other person


class DebtState(models.TextChoices):
    OPEN = "open", "Ochiq"
    PARTIAL = "partial", "Qisman qaytarilgan"
    CLOSED = "closed", "Yopilgan"
    CANCELLED = "cancelled", "Bekor qilingan"


# States the user can still mutate (repay / cancel).
ACTIVE_STATES: frozenset[str] = frozenset({DebtState.OPEN.value, DebtState.PARTIAL.value})
TERMINAL_STATES: frozenset[str] = frozenset({DebtState.CLOSED.value, DebtState.CANCELLED.value})


class DebtQuerySet(models.QuerySet):
    """Composable read-side queries. Chain freely:
    `.for_user(u).active().lent()`.
    """

    def for_user(self, user: User) -> DebtQuerySet:
        """Owner scope (NFR11 row-level isolation)."""
        return self.filter(user=user)

    def active(self) -> DebtQuerySet:
        """Debts still on the books — open or partially repaid."""
        return self.filter(state__in=list(ACTIVE_STATES))

    def lent(self) -> DebtQuerySet:
        """Others owe me (counterparty owes the user)."""
        return self.filter(direction=DebtDirection.LENT.value)

    def borrowed(self) -> DebtQuerySet:
        """I owe others."""
        return self.filter(direction=DebtDirection.BORROWED.value)


class DebtManager(models.Manager.from_queryset(DebtQuerySet)):
    """Default manager — proxies QuerySet methods so views/services can call them."""


class Debt(models.Model):
    """One outstanding (or historical) interpersonal balance."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="debts")

    direction = models.CharField(max_length=16, choices=DebtDirection.choices)
    counterparty = models.CharField(max_length=64)
    original_amount = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    remaining_amount = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="UZS")
    expected_return_date = models.DateField(null=True, blank=True)
    state = models.CharField(
        max_length=16,
        choices=DebtState.choices,
        default=DebtState.OPEN.value,
    )
    note = models.TextField(blank=True, default="")
    # Free-text reason captured when the debt is cancelled (e.g. "forgiven").
    cancelled_reason = models.CharField(max_length=64, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DebtManager()

    class Meta:
        db_table = "debts_debt"
        ordering = ["-created_at"]
        indexes = [
            # Primary access pattern: debts screen filters by direction + state.
            models.Index(fields=["user", "state", "direction"]),
            # Used by the daily debt-due reminder (Epic 9 — Story 9.3).
            models.Index(fields=["user", "expected_return_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(original_amount__gt=0),
                name="debts_original_amount_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(remaining_amount__gte=0),
                name="debts_remaining_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(remaining_amount__lte=models.F("original_amount")),
                name="debts_remaining_le_original",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_direction_display()} {self.counterparty} "
            f"{self.remaining_amount}/{self.original_amount} {self.currency} [{self.state}]"
        )

    @property
    def is_active(self) -> bool:
        return self.state in ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES


class DebtRepayment(models.Model):
    """One partial or full repayment row under a :class:`Debt`."""

    id = models.BigAutoField(primary_key=True)
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name="repayments")
    amount = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES)
    note = models.TextField(blank=True, default="")
    repaid_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "debts_debtrepayment"
        ordering = ["repaid_at", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="debts_repayment_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Repayment {self.amount} on debt {self.debt_id}"
