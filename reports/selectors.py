"""Read-side aggregations for Reports (Epic 8 Story 8.1).

Pure functions over the ORM — no writes, no fetches, no view code. Every
aggregation:

  * keeps Decimal precision (never float) and quantizes only at the boundary,
  * runs in a small, bounded number of queries (selectors are mobile-perf
    critical per NFR5),
  * accepts an ``include_debts`` flag so the same selector serves both the
    "Qarzlarni ko'rsatish" toggle (debts in totals) and the default (cash only),
  * pivots through UZS via :func:`currencies.services.safe_convert_for_display`
    when a foreign-currency display is requested; if a rate is missing we
    silently drop the row and mark ``is_fully_supported = False`` so the view
    can render a hint.

The shape returned mirrors the templates the view layer will render, so the
view should be a thin selector → context-dict adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from accounts.models import User
from transactions.models import Transaction

DISPLAY_QUANTUM = Decimal("0.01")

EXPENSE_OUTFLOW = "expense"
INCOME_INFLOW = "income"
DEBT_LENT = "debt_lent"  # money out (I gave) — counts as expense when included
DEBT_BORROWED = "debt_borrowed"  # money in (I received) — counts as income when included


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(DISPLAY_QUANTUM, rounding=ROUND_HALF_UP)


# ---------- shared data classes ----------


@dataclass(frozen=True)
class CategoryBreakdown:
    """One slice of a pie / one row of a top-N table."""

    slug: str
    name: str
    emoji: str
    total: Decimal
    percent: Decimal  # 0..100, 1dp


@dataclass(frozen=True)
class DayPoint:
    """One bar in the weekly daily-spending chart."""

    day: date
    label: str  # Du, Se, Ch, Pa, Ju, Sh, Ya
    total: Decimal


@dataclass(frozen=True)
class MonthPoint:
    """One bar in the yearly month chart."""

    month: int
    label: str
    income: Decimal
    expense: Decimal
    has_data: bool


@dataclass(frozen=True)
class CurrencySplit:
    """Per-source-currency raw totals (no conversion, for the multi-currency section)."""

    currency: str
    income: Decimal
    expense: Decimal
    transaction_count: int


@dataclass(frozen=True)
class TopExpense:
    """One row of Top N category expenses."""

    slug: str
    name: str
    emoji: str
    amount: Decimal


@dataclass(frozen=True)
class WeeklySummary:
    start: date
    end: date
    currency: str
    total_income: Decimal
    total_expense: Decimal
    by_category: list[CategoryBreakdown]
    by_day: list[DayPoint]
    transaction_count: int
    include_debts: bool
    is_fully_supported: bool

    @property
    def is_empty(self) -> bool:
        return self.transaction_count == 0

    @property
    def delta(self) -> Decimal:
        return self.total_income - self.total_expense


@dataclass(frozen=True)
class MonthlySummary:
    year: int
    month: int
    start: date
    end: date
    currency: str
    total_income: Decimal
    total_expense: Decimal
    by_category: list[CategoryBreakdown]
    top_5_expenses: list[TopExpense]
    per_currency: list[CurrencySplit]
    transaction_count: int
    include_debts: bool
    is_fully_supported: bool

    @property
    def is_empty(self) -> bool:
        return self.transaction_count == 0

    @property
    def delta(self) -> Decimal:
        return self.total_income - self.total_expense


@dataclass(frozen=True)
class YearlySummary:
    year: int
    currency: str
    total_income: Decimal
    total_expense: Decimal
    by_month: list[MonthPoint]
    top_categories: list[CategoryBreakdown]
    most_expensive_month: MonthPoint | None
    months_with_data: int
    previous_year_total_expense: Decimal | None
    include_debts: bool
    is_fully_supported: bool

    @property
    def is_partial(self) -> bool:
        return self.months_with_data < 3

    @property
    def is_empty(self) -> bool:
        return self.months_with_data == 0


# ---------- helpers ----------


def _expense_types(include_debts: bool) -> list[str]:
    return [EXPENSE_OUTFLOW, DEBT_LENT] if include_debts else [EXPENSE_OUTFLOW]


def _income_types(include_debts: bool) -> list[str]:
    return [INCOME_INFLOW, DEBT_BORROWED] if include_debts else [INCOME_INFLOW]


def _convert(amount: Decimal, from_ccy: str, to_ccy: str, on_date: date) -> Decimal | None:
    """Pivot through UZS via the currencies service. Returns None on missing-rate."""
    if from_ccy == to_ccy:
        return _quantize(amount)
    from currencies.services import safe_convert_for_display

    result = safe_convert_for_display(amount, from_ccy, to_ccy, as_of_date=on_date)
    if result is None:
        return None
    return result.amount


def _percent(part: Decimal, whole: Decimal) -> Decimal:
    if whole == 0:
        return Decimal("0.0")
    return (part / whole * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def week_bounds(today: date) -> tuple[date, date]:
    """Monday → Sunday window containing ``today`` (UZ uses Monday-start weeks)."""
    weekday = today.weekday()
    start = today - timedelta(days=weekday)
    end = start + timedelta(days=6)
    return start, end


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


UZ_DAY_INITIALS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
UZ_MONTH_SHORT = [
    "Yan",
    "Fev",
    "Mar",
    "Apr",
    "May",
    "Iyn",
    "Iyl",
    "Avg",
    "Sen",
    "Okt",
    "Noy",
    "Dek",
]


# ---------- core aggregator ----------


def _period_totals(
    user: User,
    *,
    start: date,
    end: date,
    display_currency: str,
    include_debts: bool,
    today_for_rates: date,
) -> tuple[Decimal, Decimal, int, list[CurrencySplit], bool]:
    """Two single-shot queries — totals by (currency, type) + count by currency.

    Returns (total_income_display, total_expense_display, tx_count, per_currency,
    fully_supported). ``per_currency`` is the raw (un-converted) split used by
    the multi-currency strip in the monthly view.
    """
    expense_types = _expense_types(include_debts)
    income_types = _income_types(include_debts)
    all_types = expense_types + income_types

    sum_rows = (
        Transaction.objects.for_user(user)
        .in_period(start, end)
        .filter(type__in=all_types)
        .values("currency", "type")
        .annotate(total=Sum("amount"))
    )
    count_rows = (
        Transaction.objects.for_user(user)
        .in_period(start, end)
        .filter(type__in=all_types)
        .values("currency")
        .annotate(c=Count("id"))
    )
    count_map = {row["currency"]: row["c"] for row in count_rows}

    per_ccy_in: dict[str, Decimal] = {}
    per_ccy_out: dict[str, Decimal] = {}
    for row in sum_rows:
        ccy = row["currency"]
        total = row["total"] or Decimal("0")
        if row["type"] in income_types:
            per_ccy_in[ccy] = per_ccy_in.get(ccy, Decimal("0")) + total
        else:
            per_ccy_out[ccy] = per_ccy_out.get(ccy, Decimal("0")) + total

    total_income = Decimal("0")
    total_expense = Decimal("0")
    fully_supported = True
    splits: list[CurrencySplit] = []
    all_currencies = sorted(
        set(per_ccy_in.keys()) | set(per_ccy_out.keys()) | set(count_map.keys())
    )
    for ccy in all_currencies:
        income_raw = per_ccy_in.get(ccy, Decimal("0"))
        expense_raw = per_ccy_out.get(ccy, Decimal("0"))
        splits.append(
            CurrencySplit(
                currency=ccy,
                income=_quantize(income_raw),
                expense=_quantize(expense_raw),
                transaction_count=count_map.get(ccy, 0),
            )
        )
        income_conv = _convert(income_raw, ccy, display_currency, today_for_rates)
        expense_conv = _convert(expense_raw, ccy, display_currency, today_for_rates)
        if income_conv is None or expense_conv is None:
            fully_supported = False
            continue
        total_income += income_conv
        total_expense += expense_conv

    tx_count = sum(count_map.values())
    return (
        _quantize(total_income),
        _quantize(total_expense),
        tx_count,
        splits,
        fully_supported,
    )


def _category_breakdown(
    user: User,
    *,
    start: date,
    end: date,
    display_currency: str,
    include_debts: bool,
    today_for_rates: date,
    top_n: int = 6,
) -> list[CategoryBreakdown]:
    """Top-N expense categories + a single 'Boshqalar' bucket for the tail."""
    expense_types = _expense_types(include_debts)
    rows = (
        Transaction.objects.for_user(user)
        .in_period(start, end)
        .filter(type__in=expense_types, category__isnull=False)
        .values(
            "category__slug",
            "category__name",
            "category__emoji",
            "currency",
        )
        .annotate(total=Sum("amount"))
    )

    bucket: dict[str, dict] = {}
    for row in rows:
        slug = row["category__slug"]
        amount_disp = _convert(
            row["total"] or Decimal("0"),
            row["currency"],
            display_currency,
            today_for_rates,
        )
        if amount_disp is None:
            continue
        entry = bucket.setdefault(
            slug,
            {
                "slug": slug,
                "name": row["category__name"],
                "emoji": row["category__emoji"],
                "total": Decimal("0"),
            },
        )
        entry["total"] += amount_disp

    if not bucket:
        return []

    grand_total = sum((e["total"] for e in bucket.values()), Decimal("0"))
    ordered = sorted(bucket.values(), key=lambda e: e["total"], reverse=True)

    head = ordered[:top_n]
    tail = ordered[top_n:]
    result = [
        CategoryBreakdown(
            slug=e["slug"],
            name=e["name"],
            emoji=e["emoji"],
            total=_quantize(e["total"]),
            percent=_percent(e["total"], grand_total),
        )
        for e in head
    ]
    if tail:
        tail_total = sum((e["total"] for e in tail), Decimal("0"))
        result.append(
            CategoryBreakdown(
                slug="__other__",
                name="Boshqalar",
                emoji="•",
                total=_quantize(tail_total),
                percent=_percent(tail_total, grand_total),
            )
        )
    return result


def _daily_points(
    user: User,
    *,
    start: date,
    end: date,
    display_currency: str,
    include_debts: bool,
    today_for_rates: date,
) -> list[DayPoint]:
    """One DayPoint per day in [start, end], expenses summed and converted."""
    expense_types = _expense_types(include_debts)
    rows = (
        Transaction.objects.for_user(user)
        .in_period(start, end)
        .filter(type__in=expense_types)
        .values("date", "currency")
        .annotate(total=Sum("amount"))
    )
    bucket: dict[date, Decimal] = {}
    for row in rows:
        amount_disp = _convert(
            row["total"] or Decimal("0"),
            row["currency"],
            display_currency,
            today_for_rates,
        )
        if amount_disp is None:
            continue
        bucket[row["date"]] = bucket.get(row["date"], Decimal("0")) + amount_disp

    out: list[DayPoint] = []
    cursor = start
    while cursor <= end:
        out.append(
            DayPoint(
                day=cursor,
                label=UZ_DAY_INITIALS[cursor.weekday()],
                total=_quantize(bucket.get(cursor, Decimal("0"))),
            )
        )
        cursor += timedelta(days=1)
    return out


def _top_n_expenses(
    user: User,
    *,
    start: date,
    end: date,
    display_currency: str,
    include_debts: bool,
    today_for_rates: date,
    n: int,
) -> list[TopExpense]:
    """Top-N expense categories in the period (display currency, no Boshqalar)."""
    expense_types = _expense_types(include_debts)
    rows = (
        Transaction.objects.for_user(user)
        .in_period(start, end)
        .filter(type__in=expense_types, category__isnull=False)
        .values(
            "category__slug",
            "category__name",
            "category__emoji",
            "currency",
        )
        .annotate(total=Sum("amount"))
    )
    bucket: dict[str, dict] = {}
    for row in rows:
        slug = row["category__slug"]
        amount_disp = _convert(
            row["total"] or Decimal("0"),
            row["currency"],
            display_currency,
            today_for_rates,
        )
        if amount_disp is None:
            continue
        entry = bucket.setdefault(
            slug,
            {
                "slug": slug,
                "name": row["category__name"],
                "emoji": row["category__emoji"],
                "total": Decimal("0"),
            },
        )
        entry["total"] += amount_disp
    ordered = sorted(bucket.values(), key=lambda e: e["total"], reverse=True)[:n]
    return [
        TopExpense(
            slug=e["slug"],
            name=e["name"],
            emoji=e["emoji"],
            amount=_quantize(e["total"]),
        )
        for e in ordered
    ]


# ---------- public selectors ----------


def weekly_summary(
    user: User,
    start_date: date | None = None,
    currency: str = "UZS",
    *,
    include_debts: bool = False,
    today: date | None = None,
) -> WeeklySummary:
    """Week containing ``start_date`` (Monday-anchored), aggregated for the user.

    ``start_date`` may be any date inside the desired week; the selector
    snaps to the Monday-to-Sunday window. ``today`` controls which exchange
    rate to use — defaults to the user's local "today".
    """
    today = today or timezone.localdate()
    anchor = start_date or today
    start, end = week_bounds(anchor)
    total_income, total_expense, tx_count, _splits, fully_supported = _period_totals(
        user,
        start=start,
        end=end,
        display_currency=currency,
        include_debts=include_debts,
        today_for_rates=today,
    )
    by_category = _category_breakdown(
        user,
        start=start,
        end=end,
        display_currency=currency,
        include_debts=include_debts,
        today_for_rates=today,
        top_n=6,
    )
    by_day = _daily_points(
        user,
        start=start,
        end=end,
        display_currency=currency,
        include_debts=include_debts,
        today_for_rates=today,
    )
    return WeeklySummary(
        start=start,
        end=end,
        currency=currency,
        total_income=total_income,
        total_expense=total_expense,
        by_category=by_category,
        by_day=by_day,
        transaction_count=tx_count,
        include_debts=include_debts,
        is_fully_supported=fully_supported,
    )


def monthly_summary(
    user: User,
    year: int | None = None,
    month: int | None = None,
    currency: str = "UZS",
    *,
    include_debts: bool = False,
    today: date | None = None,
) -> MonthlySummary:
    """Calendar-month aggregation with Top 5 + per-currency split."""
    today = today or timezone.localdate()
    year = year or today.year
    month = month or today.month
    start, end = month_bounds(year, month)
    total_income, total_expense, tx_count, splits, fully_supported = _period_totals(
        user,
        start=start,
        end=end,
        display_currency=currency,
        include_debts=include_debts,
        today_for_rates=today,
    )
    by_category = _category_breakdown(
        user,
        start=start,
        end=end,
        display_currency=currency,
        include_debts=include_debts,
        today_for_rates=today,
        top_n=6,
    )
    top_5 = _top_n_expenses(
        user,
        start=start,
        end=end,
        display_currency=currency,
        include_debts=include_debts,
        today_for_rates=today,
        n=5,
    )
    return MonthlySummary(
        year=year,
        month=month,
        start=start,
        end=end,
        currency=currency,
        total_income=total_income,
        total_expense=total_expense,
        by_category=by_category,
        top_5_expenses=top_5,
        per_currency=splits,
        transaction_count=tx_count,
        include_debts=include_debts,
        is_fully_supported=fully_supported,
    )


def yearly_summary(
    user: User,
    year: int | None = None,
    currency: str = "UZS",
    *,
    include_debts: bool = False,
    today: date | None = None,
) -> YearlySummary:
    """Calendar-year aggregation, always emits 12 months (gaps marked has_data=False)."""
    today = today or timezone.localdate()
    year = year or today.year
    months: list[MonthPoint] = []
    months_with_data = 0
    grand_income = Decimal("0")
    grand_expense = Decimal("0")
    fully_supported = True
    for m in range(1, 13):
        start, end = month_bounds(year, m)
        income, expense, count, _splits, supported = _period_totals(
            user,
            start=start,
            end=end,
            display_currency=currency,
            include_debts=include_debts,
            today_for_rates=today,
        )
        if not supported:
            fully_supported = False
        has = count > 0
        if has:
            months_with_data += 1
        months.append(
            MonthPoint(
                month=m,
                label=UZ_MONTH_SHORT[m - 1],
                income=income,
                expense=expense,
                has_data=has,
            )
        )
        grand_income += income
        grand_expense += expense

    most_expensive_month: MonthPoint | None = None
    for point in months:
        if not point.has_data:
            continue
        if most_expensive_month is None or point.expense > most_expensive_month.expense:
            most_expensive_month = point

    by_category = _category_breakdown(
        user,
        start=date(year, 1, 1),
        end=date(year, 12, 31),
        display_currency=currency,
        include_debts=include_debts,
        today_for_rates=today,
        top_n=5,
    )

    previous_year_total_expense: Decimal | None = None
    _prev_income, prev_expense, prev_count, _prev_splits, _prev_supported = _period_totals(
        user,
        start=date(year - 1, 1, 1),
        end=date(year - 1, 12, 31),
        display_currency=currency,
        include_debts=include_debts,
        today_for_rates=today,
    )
    if prev_count > 0:
        previous_year_total_expense = prev_expense

    return YearlySummary(
        year=year,
        currency=currency,
        total_income=_quantize(grand_income),
        total_expense=_quantize(grand_expense),
        by_month=months,
        top_categories=by_category,
        most_expensive_month=most_expensive_month,
        months_with_data=months_with_data,
        previous_year_total_expense=previous_year_total_expense,
        include_debts=include_debts,
        is_fully_supported=fully_supported,
    )


__all__ = [
    "CategoryBreakdown",
    "CurrencySplit",
    "DayPoint",
    "MonthPoint",
    "MonthlySummary",
    "TopExpense",
    "WeeklySummary",
    "YearlySummary",
    "month_bounds",
    "monthly_summary",
    "week_bounds",
    "weekly_summary",
    "yearly_summary",
]
