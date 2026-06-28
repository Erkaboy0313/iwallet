"""Read-side aggregations for debts (Stories 4.3 + 4.4).

Selectors are pure functions over the ORM — no writes, no side effects.
Views call them; tests pin their behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, QuerySet, Sum

from accounts.models import User

from .models import Debt, DebtDirection


@dataclass(frozen=True)
class CurrencyTotal:
    """One line in the per-currency total strip at the top of each tab."""

    currency: str
    total: Decimal


@dataclass(frozen=True)
class DebtStatusSummary:
    """Compact snapshot used by Home BalanceHero (Story 4.4)."""

    open_lent_count: int  # how many people owe me
    open_borrowed_count: int  # how many people I owe
    # Net effect on the user's net worth, per currency
    # (positive → I am net owed, negative → I net owe).
    lent_remaining_by_currency: dict[str, Decimal]
    borrowed_remaining_by_currency: dict[str, Decimal]

    @property
    def has_any(self) -> bool:
        return bool(self.open_lent_count or self.open_borrowed_count)


def active_debts_for(user: User, *, direction: str) -> QuerySet[Debt]:
    """Active (open + partial) debts in one direction, newest first.

    Uses the `(user, state, direction)` composite index from Story 4.1.
    """
    if direction not in {DebtDirection.LENT.value, DebtDirection.BORROWED.value}:
        raise ValueError(f"Unknown direction: {direction!r}")
    return Debt.objects.for_user(user).active().filter(direction=direction).order_by("-created_at")


def totals_by_currency(qs: QuerySet[Debt]) -> list[CurrencyTotal]:
    """Sum remaining_amount per currency for the given debt queryset."""
    rows = qs.values("currency").annotate(total=Sum("remaining_amount")).order_by("currency")
    return [
        CurrencyTotal(currency=row["currency"], total=row["total"] or Decimal("0")) for row in rows
    ]


def debt_status_summary(user: User) -> DebtStatusSummary:
    """Snapshot for Home BalanceHero: how many active debts in each direction."""
    active = Debt.objects.for_user(user).active()

    counts = active.values("direction").annotate(c=Count("id"))
    count_map = {row["direction"]: row["c"] for row in counts}

    sums = active.values("direction", "currency").annotate(total=Sum("remaining_amount"))
    lent_map: dict[str, Decimal] = {}
    borrowed_map: dict[str, Decimal] = {}
    for row in sums:
        target = lent_map if row["direction"] == DebtDirection.LENT.value else borrowed_map
        target[row["currency"]] = row["total"] or Decimal("0")

    return DebtStatusSummary(
        open_lent_count=count_map.get(DebtDirection.LENT.value, 0),
        open_borrowed_count=count_map.get(DebtDirection.BORROWED.value, 0),
        lent_remaining_by_currency=lent_map,
        borrowed_remaining_by_currency=borrowed_map,
    )


def get_user_debt(user: User, debt_id: int) -> Debt | None:
    """Single-debt lookup scoped to the user (None on miss/cross-tenant)."""
    return Debt.objects.for_user(user).filter(pk=debt_id).first()


def initials_for(name: str) -> str:
    """Two-letter avatar initials. 'Akram Tursun' -> 'AT'; 'Akram' -> 'AK'."""
    cleaned = (name or "").strip()
    if not cleaned:
        return "?"
    parts = cleaned.split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()
