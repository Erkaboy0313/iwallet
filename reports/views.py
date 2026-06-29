"""Reports views (Epic 8 Stories 8.2 / 8.3 / 8.4).

Each view follows the same pattern:

  1. Resolve display currency from session + user preferences.
  2. Parse period from query string (?week=YYYY-MM-DD, ?month=YYYY-MM,
     ?year=YYYY) — bad input snaps to "current".
  3. Run the matching selector.
  4. Build chart SVGs + nav links via the services helper layer.
  5. Render the template.

Templates render as the full chrome on GET and as the inner content partial on
htmx swap so the tab pills + chrome stay put when only the period changes.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from reports.selectors import (
    monthly_summary,
    weekly_summary,
    yearly_summary,
)
from reports.services import (
    build_monthly_io_bars_svg,
    build_monthly_pie_svg,
    build_weekly_bars_svg,
    build_weekly_pie_svg,
    build_yearly_bars_svg,
    compute_yoy_delta,
    format_month_label,
    format_week_label,
    month_nav_links,
    parse_include_debts,
    parse_month,
    parse_week,
    parse_year,
    resolve_display_currency,
    tab_links,
    week_nav_links,
    year_nav_links,
)


def _toggle_debts_url(view_name: str, params: dict, include_debts: bool) -> str:
    """URL that flips the include_debts flag, keeping the active period."""
    flipped = dict(params)
    if not include_debts:
        flipped["include_debts"] = "1"
    return f"{reverse(view_name)}?{urlencode(flipped)}"


@require_GET
def weekly_view(request):
    """Weekly report — pie + daily bars (Story 8.2)."""
    today = timezone.localdate()
    anchor = parse_week(request, today=today)
    include_debts = parse_include_debts(request)
    display_currency = resolve_display_currency(request, request.user)

    summary = weekly_summary(
        request.user,
        anchor,
        display_currency,
        include_debts=include_debts,
        today=today,
    )

    pie_svg = build_weekly_pie_svg(summary)
    bars_svg = build_weekly_bars_svg(summary)
    nav = week_nav_links(summary.start, include_debts=include_debts, today=today)
    toggle_url = _toggle_debts_url(
        "reports:weekly",
        {"week": summary.start.isoformat()},
        include_debts,
    )

    context = {
        "summary": summary,
        "display_currency": display_currency,
        "include_debts": include_debts,
        "pie_svg": pie_svg,
        "bars_svg": bars_svg,
        "nav": nav,
        "toggle_debts_url": toggle_url,
        "period_label": format_week_label(summary.start, summary.end),
        "tabs": tab_links("weekly"),
    }
    template = (
        "reports/_weekly_content.html"
        if request.headers.get("HX-Request")
        else "reports/weekly.html"
    )
    return render(request, template, context)


@require_GET
def monthly_view(request):
    """Monthly report — pie + IO comparison + top 5 + per-currency split (Story 8.3)."""
    today = timezone.localdate()
    year, month = parse_month(request, today=today)
    include_debts = parse_include_debts(request)
    display_currency = resolve_display_currency(request, request.user)

    summary = monthly_summary(
        request.user,
        year,
        month,
        display_currency,
        include_debts=include_debts,
        today=today,
    )

    pie_svg = build_monthly_pie_svg(summary)
    io_bars_svg = build_monthly_io_bars_svg(summary)
    nav = month_nav_links(year, month, include_debts=include_debts, today=today)
    toggle_url = _toggle_debts_url(
        "reports:monthly",
        {"month": f"{year:04d}-{month:02d}"},
        include_debts,
    )

    # Filter out the active display ccy from the multi-ccy strip — that's the
    # one already represented in the headline totals.
    other_currencies = [
        row
        for row in summary.per_currency
        if row.currency != display_currency and row.transaction_count > 0
    ]

    context = {
        "summary": summary,
        "display_currency": display_currency,
        "include_debts": include_debts,
        "pie_svg": pie_svg,
        "io_bars_svg": io_bars_svg,
        "nav": nav,
        "toggle_debts_url": toggle_url,
        "period_label": format_month_label(year, month),
        "tabs": tab_links("monthly"),
        "other_currencies": other_currencies,
    }
    template = (
        "reports/_monthly_content.html"
        if request.headers.get("HX-Request")
        else "reports/monthly.html"
    )
    return render(request, template, context)


@require_GET
def yearly_view(request):
    """Yearly report — 12 month bars + partial-data hint + top categories (Story 8.4)."""
    today = timezone.localdate()
    year = parse_year(request, today=today)
    include_debts = parse_include_debts(request)
    display_currency = resolve_display_currency(request, request.user)

    summary = yearly_summary(
        request.user,
        year,
        display_currency,
        include_debts=include_debts,
        today=today,
    )

    bars_svg = build_yearly_bars_svg(summary)
    nav = year_nav_links(year, include_debts=include_debts, today=today)
    toggle_url = _toggle_debts_url(
        "reports:yearly",
        {"year": str(year)},
        include_debts,
    )
    yoy_pct = compute_yoy_delta(summary.total_expense, summary.previous_year_total_expense)

    context = {
        "summary": summary,
        "display_currency": display_currency,
        "include_debts": include_debts,
        "bars_svg": bars_svg,
        "nav": nav,
        "toggle_debts_url": toggle_url,
        "period_label": str(year),
        "tabs": tab_links("yearly"),
        "yoy_pct": yoy_pct,
    }
    template = (
        "reports/_yearly_content.html"
        if request.headers.get("HX-Request")
        else "reports/yearly.html"
    )
    return render(request, template, context)
