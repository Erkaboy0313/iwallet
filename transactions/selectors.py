"""Read-side aggregations for transactions (Story 1.5+)."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, QuerySet, Sum

from accounts.models import User

from .models import Transaction


@dataclass(frozen=True)
class TopCategory:
    slug: str
    name: str
    emoji: str
    total: Decimal
    share_pct: float = 0.0  # 0..100, share of this month's total expense.


@dataclass(frozen=True)
class DailyAmount:
    day: date
    amount: Decimal


@dataclass(frozen=True)
class CashFlowDelta:
    """Month-over-month cash position delta (Sprint v0.6 §2.4 Home delta line)."""

    previous_balance: Decimal
    delta: Decimal  # current_balance - previous_balance
    direction: str  # "up" / "down" / "flat"
    has_previous: bool  # False on the first month of activity → caller hides the row.


@dataclass(frozen=True)
class MonthSummary:
    # Cash position = inflow_total − outflow_total. inflow_total is income +
    # debt_borrowed (cash arrived this month, regardless of source). outflow_total
    # is expense + debt_lent. Sprint v0.5 fix: borrowing money now increases
    # cash, lending decreases it. The remaining debt obligation is still
    # tracked separately by debts.selectors.debt_status_summary.
    cash_balance: Decimal
    inflow_total: Decimal
    outflow_total: Decimal
    total_income: Decimal
    total_expense: Decimal
    total_debt_borrowed: Decimal
    total_debt_lent: Decimal
    currency: str
    top_categories: list[TopCategory]
    transaction_count: int

    @property
    def is_empty(self) -> bool:
        return self.transaction_count == 0


def all_time_cash_balance(user: User, currency: str = "UZS") -> Decimal:
    """User's all-time cash position in a single source currency.

    Sum inflow (income + debt_borrowed) minus outflow (expense + debt_lent)
    over every transaction ever recorded — no month cutoff. Powers the
    home hero so the first of the month doesn't look like all previous
    money vanished.
    """
    qs = Transaction.objects.for_user(user).filter(currency=currency)
    by_type = qs.values("type").annotate(total=Sum("amount"))
    totals = {row["type"]: row["total"] or Decimal("0") for row in by_type}
    inflow = totals.get("income", Decimal("0")) + totals.get("debt_borrowed", Decimal("0"))
    outflow = totals.get("expense", Decimal("0")) + totals.get("debt_lent", Decimal("0"))
    return inflow - outflow


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
    """Snapshot of the current month for the BalanceHero (Sprint v0.5 fix).

    Cash math now includes debts: borrowing brings cash in, lending takes
    cash out. The standing debt obligation is still tracked separately by
    `debts.selectors.debt_status_summary` — this selector only describes the
    cash flow for the month.

    Perf: one aggregation grouped by type instead of 4 separate Sum() queries
    + one count call. Top-categories stays a separate query (different group
    key + LIMIT 3). Total: 2 queries per call, down from 6.
    """
    start, end = _month_bounds(today)
    qs = Transaction.objects.for_user(user).in_period(start, end).filter(currency=currency)

    by_type = qs.values("type").annotate(total=Sum("amount"), n=Count("id"))
    totals: dict[str, tuple[Decimal, int]] = {
        row["type"]: (row["total"] or Decimal("0"), row["n"]) for row in by_type
    }

    income_total, income_n = totals.get("income", (Decimal("0"), 0))
    expense_total, expense_n = totals.get("expense", (Decimal("0"), 0))
    borrowed_total, borrowed_n = totals.get("debt_borrowed", (Decimal("0"), 0))
    lent_total, lent_n = totals.get("debt_lent", (Decimal("0"), 0))

    inflow_total = income_total + borrowed_total
    outflow_total = expense_total + lent_total
    transaction_count = income_n + expense_n + borrowed_n + lent_n

    top_qs = (
        qs.by_type("expense")
        .filter(category__isnull=False)
        .values("category__slug", "category__name", "category__emoji")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:3]
    )
    top_max = top_qs[0]["total"] if top_qs else Decimal("0")
    top = [
        TopCategory(
            slug=row["category__slug"],
            name=row["category__name"],
            emoji=row["category__emoji"],
            total=row["total"],
            share_pct=float(row["total"]) / float(top_max) * 100 if top_max else 0.0,
        )
        for row in top_qs
    ]

    return MonthSummary(
        cash_balance=inflow_total - outflow_total,
        inflow_total=inflow_total,
        outflow_total=outflow_total,
        total_income=income_total,
        total_expense=expense_total,
        total_debt_borrowed=borrowed_total,
        total_debt_lent=lent_total,
        currency=currency,
        top_categories=top,
        transaction_count=transaction_count,
    )


def daily_flow_series(
    user: User,
    currency: str,
    *,
    days: int = 14,
    today: date | None = None,
) -> tuple[list[DailyAmount], list[DailyAmount]]:
    """Per-day inflow + outflow for the last `days` days, oldest first.

    Drives the sparklines on the Home inflow/outflow cards (Sprint v0.6 §2.4).
    Returns (inflow_series, outflow_series) — both length `days`, zero-filled
    for days without activity so the SVG x-axis is uniform.
    """
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    qs = (
        Transaction.objects.for_user(user)
        .in_period(start, today)
        .filter(currency=currency)
        .values("date", "type")
        .annotate(total=Sum("amount"))
    )
    in_by_day: dict[date, Decimal] = {}
    out_by_day: dict[date, Decimal] = {}
    for row in qs:
        d = row["date"]
        amount = row["total"] or Decimal("0")
        if row["type"] in {"income", "debt_borrowed"}:
            in_by_day[d] = in_by_day.get(d, Decimal("0")) + amount
        elif row["type"] in {"expense", "debt_lent"}:
            out_by_day[d] = out_by_day.get(d, Decimal("0")) + amount

    inflow_series: list[DailyAmount] = []
    outflow_series: list[DailyAmount] = []
    for offset in range(days):
        d = start + timedelta(days=offset)
        inflow_series.append(DailyAmount(day=d, amount=in_by_day.get(d, Decimal("0"))))
        outflow_series.append(DailyAmount(day=d, amount=out_by_day.get(d, Decimal("0"))))
    return inflow_series, outflow_series


def month_over_month_delta(
    user: User,
    currency: str,
    *,
    today: date | None = None,
    current: "MonthSummary | None" = None,
) -> CashFlowDelta:
    """Compare this month's cash position vs last month's same selector.

    Used by the Home big-balance card's delta caption. Pass an already-
    computed `current` summary to skip the redundant DB query — the home
    view does this since it already has the current month cached.
    """
    today = today or date.today()
    last_month_anchor = (today.replace(day=1) - timedelta(days=1)).replace(day=15)
    if current is None:
        current = month_summary(user, currency, today=today)
    previous = month_summary(user, currency, today=last_month_anchor)
    delta = current.cash_balance - previous.cash_balance
    if previous.is_empty:
        return CashFlowDelta(
            previous_balance=Decimal("0"),
            delta=Decimal("0"),
            direction="flat",
            has_previous=False,
        )
    if delta > 0:
        direction = "up"
    elif delta < 0:
        direction = "down"
    else:
        direction = "flat"
    return CashFlowDelta(
        previous_balance=previous.cash_balance,
        delta=delta,
        direction=direction,
        has_previous=True,
    )


def history_list(
    user: User,
    *,
    type_: str | None = None,
    category_slug: str | None = None,
    currency: str | None = None,
    start: date | None = None,
    end: date | None = None,
) -> QuerySet[Transaction]:
    """Reverse-chronological history with optional filters (Story 1.6).

    Includes select_related('category') so list templates avoid the N+1 trap.
    """
    qs = (
        Transaction.objects.for_user(user)
        .select_related("category")
        .order_by("-date", "-created_at")
    )
    if type_:
        qs = qs.by_type(type_)
    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if currency:
        qs = qs.filter(currency=currency)
    if start is not None and end is not None:
        qs = qs.in_period(start, end)
    return qs
