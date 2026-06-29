"""Reports view helpers (Epic 8).

The views themselves stay thin — they parse query params, pull the report
summary via selectors, then ask helpers in here to build the things templates
can't easily compute (chart SVGs, prev/next nav links, display-mode resolution).

No DB writes happen here; this is a pure adapter layer between selectors and
templates so the views can stay free of business logic.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from currencies.constants import CURRENCY_CODES
from currencies.views import SESSION_DISPLAY_CURRENCY
from reports.charts import BarPoint, PieSlice, svg_bar, svg_pie

# ---------- display preference helpers ----------


def resolve_display_currency(request: HttpRequest, user: User) -> str:
    """Pick the reports' source currency — always the user's default.

    Reports show transactions in their source currency; the home balance
    switcher does NOT propagate here. If the user wants to look at RUB
    transactions specifically they'll change their default currency in
    Settings (or future Sprint v0.8 will add a per-report ccy filter).
    """
    currency = request.session.get(SESSION_DISPLAY_CURRENCY) or user.default_currency
    if currency not in CURRENCY_CODES:
        currency = "UZS"
    return currency


# ---------- query-string parsers ----------


def parse_week(request: HttpRequest, today: date | None = None) -> date:
    """Read the ?week=YYYY-MM-DD param; fall back to today.

    Tolerates a missing/garbage param without 500'ing — bad input quietly snaps
    to "current week" so the view always renders.
    """
    today = today or timezone.localdate()
    raw = request.GET.get("week", "")
    if not raw:
        return today
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return today


def parse_month(request: HttpRequest, today: date | None = None) -> tuple[int, int]:
    """Read ?month=YYYY-MM; fall back to current month."""
    today = today or timezone.localdate()
    raw = request.GET.get("month", "")
    if not raw:
        return today.year, today.month
    try:
        year_s, month_s = raw.split("-")
        return int(year_s), int(month_s)
    except (ValueError, AttributeError):
        return today.year, today.month


def parse_year(request: HttpRequest, today: date | None = None) -> int:
    today = today or timezone.localdate()
    raw = request.GET.get("year", "")
    if not raw:
        return today.year
    try:
        return int(raw)
    except ValueError:
        return today.year


def parse_include_debts(request: HttpRequest) -> bool:
    return request.GET.get("include_debts", "").lower() in {"1", "true", "on", "yes"}


# ---------- prev/next navigation ----------


def _build_qs(base: dict, *, include_debts: bool) -> str:
    """Encode a query string, only emitting include_debts when True."""
    out = dict(base)
    if include_debts:
        out["include_debts"] = "1"
    return urlencode(out)


def week_nav_links(start: date, *, include_debts: bool, today: date) -> dict:
    prev_week = start - timedelta(days=7)
    next_week = start + timedelta(days=7)
    weekly_url = reverse("reports:weekly")
    return {
        "prev_url": f"{weekly_url}?{_build_qs({'week': prev_week.isoformat()}, include_debts=include_debts)}",
        "next_url": f"{weekly_url}?{_build_qs({'week': next_week.isoformat()}, include_debts=include_debts)}",
        "current_url": f"{weekly_url}?{_build_qs({}, include_debts=include_debts)}",
        "is_current_week": _same_week(start, today),
    }


def month_nav_links(year: int, month: int, *, include_debts: bool, today: date) -> dict:
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)
    monthly_url = reverse("reports:monthly")
    return {
        "prev_url": (
            f"{monthly_url}?"
            f"{_build_qs({'month': f'{prev_y:04d}-{prev_m:02d}'}, include_debts=include_debts)}"
        ),
        "next_url": (
            f"{monthly_url}?"
            f"{_build_qs({'month': f'{next_y:04d}-{next_m:02d}'}, include_debts=include_debts)}"
        ),
        "current_url": f"{monthly_url}?{_build_qs({}, include_debts=include_debts)}",
        "is_current_month": (year, month) == (today.year, today.month),
    }


def year_nav_links(year: int, *, include_debts: bool, today: date) -> dict:
    yearly_url = reverse("reports:yearly")
    return {
        "prev_url": f"{yearly_url}?{_build_qs({'year': str(year - 1)}, include_debts=include_debts)}",
        "next_url": f"{yearly_url}?{_build_qs({'year': str(year + 1)}, include_debts=include_debts)}",
        "current_url": f"{yearly_url}?{_build_qs({}, include_debts=include_debts)}",
        "is_current_year": year == today.year,
    }


def _same_week(d: date, today: date) -> bool:
    iso_a = d.isocalendar()
    iso_b = today.isocalendar()
    return iso_a.year == iso_b.year and iso_a.week == iso_b.week


# ---------- toggle URLs ----------


def toggle_debts_url(view_name: str, *, base_params: dict, include_debts: bool) -> str:
    """URL that flips the include_debts flag, preserving the period."""
    flipped = dict(base_params)
    if not include_debts:
        flipped["include_debts"] = "1"
    return f"{reverse(view_name)}?{urlencode(flipped)}"


# ---------- chart builders ----------


def build_weekly_pie_svg(summary) -> str:  # noqa: ARG001 — kept thin for monkeypatching
    slices = [
        PieSlice(
            label=row.name,
            value=row.total,
            href=(
                None
                if row.slug == "__other__"
                else f"{reverse('transactions:history')}?{urlencode({'type': 'expense'})}"
            ),
        )
        for row in summary.by_category
    ]
    return svg_pie(
        slices,
        title="Hafta kategoriyalari",
        desc="Haftalik xarajatlar kategoriyalar bo'yicha",
    )


def build_weekly_bars_svg(summary) -> str:
    points = [BarPoint(label=p.label, value=p.total) for p in summary.by_day]
    return svg_bar(
        points,
        color="#0ea5e9",
        title="Kunlik xarajatlar",
        desc="Dushanba dan Yakshanbagacha xarajatlar",
    )


def build_monthly_pie_svg(summary) -> str:
    slices = [PieSlice(label=row.name, value=row.total) for row in summary.by_category]
    return svg_pie(
        slices,
        title="Oy kategoriyalari",
        desc="Oylik xarajatlar kategoriyalar bo'yicha",
    )


def build_monthly_io_bars_svg(summary) -> str:
    """Two-bar 'kirim vs chiqim' mini chart."""
    points = [
        BarPoint(label="Kirim", value=summary.total_income),
        BarPoint(label="Chiqim", value=summary.total_expense),
    ]
    return svg_bar(
        points,
        color="#10b981",
        title="Kirim va chiqim",
        desc="Oylik kirim va chiqim taqqoslash",
    )


def build_yearly_bars_svg(summary) -> str:
    points = [BarPoint(label=p.label, value=p.expense) for p in summary.by_month]
    highlight_idx: int | None = None
    if summary.most_expensive_month is not None:
        highlight_idx = summary.most_expensive_month.month - 1
    return svg_bar(
        points,
        color="#10b981",
        title="Oylar bo'yicha xarajatlar",
        desc="Yil davomida har oygi xarajatlar",
        highlight_index=highlight_idx,
    )


# ---------- header formatting ----------


UZ_MONTH_FULL = {
    1: "Yanvar",
    2: "Fevral",
    3: "Mart",
    4: "Aprel",
    5: "May",
    6: "Iyun",
    7: "Iyul",
    8: "Avgust",
    9: "Sentabr",
    10: "Oktabr",
    11: "Noyabr",
    12: "Dekabr",
}


def format_week_label(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start.day}–{end.day} {UZ_MONTH_FULL[start.month]} {start.year}"
    return (
        f"{start.day} {UZ_MONTH_FULL[start.month]} – {end.day} {UZ_MONTH_FULL[end.month]}"
        f" {start.year if start.year == end.year else f'{start.year}/{end.year}'}"
    )


def format_month_label(year: int, month: int) -> str:
    return f"{UZ_MONTH_FULL[month]} {year}"


# ---------- summary delta helpers ----------


@dataclass(frozen=True)
class TabSpec:
    """One entry in the period switcher pill row."""

    label: str
    url: str
    is_active: bool


def tab_links(active: str) -> list[TabSpec]:
    return [
        TabSpec(
            label="Hafta",
            url=reverse("reports:weekly"),
            is_active=active == "weekly",
        ),
        TabSpec(
            label="Oy",
            url=reverse("reports:monthly"),
            is_active=active == "monthly",
        ),
        TabSpec(
            label="Yil",
            url=reverse("reports:yearly"),
            is_active=active == "yearly",
        ),
    ]


def compute_yoy_delta(this_year: Decimal, prev_year: Decimal | None) -> Decimal | None:
    """Return (this − prev) / prev * 100 rounded to 1dp; None if no prior data."""
    if prev_year is None or prev_year == 0:
        return None
    return ((this_year - prev_year) / prev_year * Decimal("100")).quantize(Decimal("0.1"))


# Suppress flake8/ruff 'unused' on stdlib imports we keep around for future helpers.
_ = calendar
