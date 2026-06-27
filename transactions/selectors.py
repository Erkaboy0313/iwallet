"""Read-side aggregations for transactions (Story 1.5+)."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from accounts.models import User

from .models import Transaction


@dataclass(frozen=True)
class TopCategory:
    slug: str
    name: str
    emoji: str
    total: Decimal


@dataclass(frozen=True)
class MonthSummary:
    cash_balance: Decimal  # income − expense (excludes debts for Story 1.5)
    total_income: Decimal
    total_expense: Decimal
    currency: str
    top_categories: list[TopCategory]
    transaction_count: int

    @property
    def is_empty(self) -> bool:
        return self.transaction_count == 0


def _month_bounds(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    first = today.replace(day=1)
    # First day of next month minus 1 day = last day of current month.
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    return first, next_first - timedelta(days=1)


def month_summary(user: User, currency: str = "UZS", *, today: date | None = None) -> MonthSummary:
    """Snapshot of the current month for the BalanceHero (Story 1.5).

    Debt accounting moves to Epic 4 — for now `cash_balance` is plain
    income − expense, and top categories cover expenses only.
    """
    start, end = _month_bounds(today)
    qs = Transaction.objects.for_user(user).in_period(start, end).filter(currency=currency)

    income_total = qs.by_type("income").aggregate(t=Sum("amount"))["t"] or Decimal("0")
    expense_total = qs.by_type("expense").aggregate(t=Sum("amount"))["t"] or Decimal("0")

    top_qs = (
        qs.by_type("expense")
        .filter(category__isnull=False)
        .values("category__slug", "category__name", "category__emoji")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:3]
    )
    top = [
        TopCategory(
            slug=row["category__slug"],
            name=row["category__name"],
            emoji=row["category__emoji"],
            total=row["total"],
        )
        for row in top_qs
    ]

    return MonthSummary(
        cash_balance=income_total - expense_total,
        total_income=income_total,
        total_expense=expense_total,
        currency=currency,
        top_categories=top,
        transaction_count=qs.count(),
    )
