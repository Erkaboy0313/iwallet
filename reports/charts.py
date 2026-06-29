"""Inline-SVG chart renderers for Reports (Epic 8 Story 8.2).

No JS dependency, no chart.js — every chart is plain SVG markup the templates
include via ``{{ svg|safe }}``. Two primitives:

  * :func:`svg_pie` — donut chart with up to 7 slices (top 6 + "Boshqalar"),
    fixed 300x300 viewport, each slice optionally wrapped in a clickable
    ``<a xlink:href>`` so the user can drill into the matching history view.
  * :func:`svg_bar` — simple categorical bar chart (one bar per label) with a
    title + desc for screen-reader access. Used by both the weekly daily bars
    and the yearly month bars.

The palette is fixed (seven swatches mapped by index) so swatches stay stable
across renders — taps on the same slice always go to the same colour.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from html import escape

# Stable palette — emerald-led, slate-tailed, mirrors UX-DR token sketch.
PALETTE = [
    "#10b981",  # emerald-500
    "#0ea5e9",  # sky-500
    "#f59e0b",  # amber-500
    "#8b5cf6",  # violet-500
    "#ef4444",  # red-500
    "#14b8a6",  # teal-500
    "#64748b",  # slate-500 (used for the "Boshqalar" bucket by convention)
]

PIE_SIZE = 300  # px / svg unit
PIE_CENTER = PIE_SIZE / 2
PIE_RADIUS = 120
PIE_INNER_RADIUS = 60  # donut hole — makes the centre legend readable

BAR_WIDTH = 320
BAR_HEIGHT = 180
BAR_PADDING_X = 16
BAR_PADDING_TOP = 16
BAR_PADDING_BOTTOM = 28  # leaves room for axis labels


@dataclass(frozen=True)
class PieSlice:
    label: str
    value: Decimal
    href: str | None = None  # None -> not clickable


@dataclass(frozen=True)
class BarPoint:
    label: str
    value: Decimal


# ---------- pie ----------


def _polar_to_xy(cx: float, cy: float, radius: float, angle_rad: float) -> tuple[float, float]:
    return cx + radius * math.cos(angle_rad), cy + radius * math.sin(angle_rad)


def _arc_path(
    cx: float, cy: float, radius_outer: float, radius_inner: float, start: float, end: float
) -> str:
    """Build an SVG donut-arc <path> 'd' string between two angles (radians).

    Uses two arcs (outer CCW, inner CW) plus straight lines on the radii so the
    slice is a closed region.
    """
    large_arc = 1 if (end - start) > math.pi else 0
    x1_out, y1_out = _polar_to_xy(cx, cy, radius_outer, start)
    x2_out, y2_out = _polar_to_xy(cx, cy, radius_outer, end)
    x1_in, y1_in = _polar_to_xy(cx, cy, radius_inner, end)
    x2_in, y2_in = _polar_to_xy(cx, cy, radius_inner, start)
    return (
        f"M {x1_out:.3f} {y1_out:.3f} "
        f"A {radius_outer} {radius_outer} 0 {large_arc} 1 {x2_out:.3f} {y2_out:.3f} "
        f"L {x1_in:.3f} {y1_in:.3f} "
        f"A {radius_inner} {radius_inner} 0 {large_arc} 0 {x2_in:.3f} {y2_in:.3f} "
        "Z"
    )


def svg_pie(
    slices: list[PieSlice],
    *,
    title: str = "Kategoriya taqsimoti",
    desc: str = "Xarajatlar kategoriyalar bo'yicha",
) -> str:
    """Render a donut chart. Empty input → centred 'ma'lumot yo'q' placeholder."""
    total = sum((s.value for s in slices), Decimal("0"))
    if total <= 0 or not slices:
        return (
            f'<svg viewBox="0 0 {PIE_SIZE} {PIE_SIZE}" role="img" '
            f'aria-label="{escape(title)}" '
            'xmlns="http://www.w3.org/2000/svg" '
            f'style="width:100%;max-width:{PIE_SIZE}px;height:auto;display:block;margin:0 auto">'
            f"<title>{escape(title)}</title>"
            f"<desc>{escape(desc)}</desc>"
            f'<circle cx="{PIE_CENTER}" cy="{PIE_CENTER}" r="{PIE_RADIUS}" '
            'fill="none" stroke="rgba(255, 255, 255, 0.14)" stroke-width="2"/>'
            f'<text x="{PIE_CENTER}" y="{PIE_CENTER + 5}" text-anchor="middle" '
            'font-size="14" fill="#A8B0A6">Ma\'lumot yo\'q</text>'
            "</svg>"
        )

    parts: list[str] = []
    angle_cursor = -math.pi / 2  # start at 12 o'clock
    for idx, sl in enumerate(slices):
        if sl.value <= 0:
            continue
        fraction = float(sl.value / total)
        end_angle = angle_cursor + fraction * 2 * math.pi
        # Tiny gap between slices so they read as distinct.
        gap = math.radians(1) if len(slices) > 1 else 0
        path = _arc_path(
            PIE_CENTER,
            PIE_CENTER,
            PIE_RADIUS,
            PIE_INNER_RADIUS,
            angle_cursor + gap / 2,
            max(end_angle - gap / 2, angle_cursor + gap / 2 + 0.0001),
        )
        color = PALETTE[idx % len(PALETTE)]
        slice_svg = (
            f'<path d="{path}" fill="{color}" '
            f'aria-label="{escape(sl.label)}: {fraction * 100:.1f}%"/>'
        )
        if sl.href:
            slice_svg = (
                f'<a xlink:href="{escape(sl.href)}" href="{escape(sl.href)}" '
                f'aria-label="{escape(sl.label)} kategoriyasiga o\'tish">{slice_svg}</a>'
            )
        parts.append(slice_svg)
        angle_cursor = end_angle

    # Centre label — total in the middle of the donut.
    parts.append(
        f'<text x="{PIE_CENTER}" y="{PIE_CENTER - 4}" text-anchor="middle" '
        'font-size="11" fill="#A8B0A6">Jami</text>'
    )
    parts.append(
        f'<text x="{PIE_CENTER}" y="{PIE_CENTER + 14}" text-anchor="middle" '
        f'font-size="16" font-weight="600" fill="#F0F4EF">{_short_number(total)}</text>'
    )

    return (
        f'<svg viewBox="0 0 {PIE_SIZE} {PIE_SIZE}" role="img" '
        f'aria-label="{escape(title)}" '
        'xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'style="width:100%;max-width:{PIE_SIZE}px;height:auto;display:block;margin:0 auto">'
        f"<title>{escape(title)}</title>"
        f"<desc>{escape(desc)}</desc>" + "".join(parts) + "</svg>"
    )


# ---------- bar ----------


def _short_number(value: Decimal) -> str:
    """Compact number formatter for the chart labels (k/mln). 2-3 chars max."""
    abs_v = abs(value)
    if abs_v >= Decimal("1000000"):
        return f"{value / Decimal('1000000'):.1f}mln"
    if abs_v >= Decimal("1000"):
        return f"{value / Decimal('1000'):.0f}k"
    if abs_v == 0:
        return "0"
    return f"{value:.0f}"


def svg_bar(
    points: list[BarPoint],
    *,
    color: str = "#10b981",
    title: str = "Bar chart",
    desc: str = "",
    highlight_index: int | None = None,
) -> str:
    """Single-color bar chart. Zero-value bars render as a thin slate stripe.

    ``highlight_index`` (used by the yearly "most expensive month" call-out)
    overrides ``color`` for one bar with an amber accent.
    """
    if not points:
        return (
            f'<svg viewBox="0 0 {BAR_WIDTH} {BAR_HEIGHT}" role="img" '
            f'aria-label="{escape(title)}" '
            'xmlns="http://www.w3.org/2000/svg" '
            'style="width:100%;height:auto;display:block">'
            f"<title>{escape(title)}</title>"
            f'<text x="{BAR_WIDTH / 2}" y="{BAR_HEIGHT / 2}" text-anchor="middle" '
            'font-size="12" fill="#A8B0A6">Ma\'lumot yo\'q</text>'
            "</svg>"
        )

    max_val = max((p.value for p in points), default=Decimal("0"))
    chart_height = BAR_HEIGHT - BAR_PADDING_TOP - BAR_PADDING_BOTTOM
    chart_width = BAR_WIDTH - 2 * BAR_PADDING_X
    bar_slot = chart_width / len(points)
    bar_width = max(bar_slot * 0.65, 6)
    # Sprint v0.6 §9.3: gradient fills for depth.
    parts: list[str] = [
        "<defs>"
        '<linearGradient id="bar-grad" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="1"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.65"/>'
        "</linearGradient>"
        '<linearGradient id="bar-grad-amber" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#f59e0b" stop-opacity="1"/>'
        '<stop offset="100%" stop-color="#f59e0b" stop-opacity="0.65"/>'
        "</linearGradient>"
        "</defs>"
    ]
    for idx, point in enumerate(points):
        slot_x = BAR_PADDING_X + idx * bar_slot
        bar_x = slot_x + (bar_slot - bar_width) / 2
        if max_val <= 0:
            h = 2
        else:
            h = max(float(point.value / max_val) * chart_height, 2 if point.value > 0 else 1)
        y = BAR_PADDING_TOP + (chart_height - h)
        fill = "url(#bar-grad)" if point.value > 0 else "#e2e8f0"
        if highlight_index is not None and idx == highlight_index and point.value > 0:
            fill = "url(#bar-grad-amber)"
        label = (
            f"{escape(point.label)}: {_short_number(point.value)}"
            if point.value
            else f"{escape(point.label)}: 0"
        )
        parts.append(
            f'<rect x="{bar_x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{h:.2f}" '
            f'rx="4" fill="{fill}"><title>{label}</title></rect>'
        )
        # Day/month label under each bar.
        parts.append(
            f'<text x="{slot_x + bar_slot / 2:.2f}" y="{BAR_HEIGHT - 10}" '
            'text-anchor="middle" font-size="10" fill="#A8B0A6">'
            f"{escape(point.label)}</text>"
        )

    return (
        f'<svg viewBox="0 0 {BAR_WIDTH} {BAR_HEIGHT}" role="img" '
        f'aria-label="{escape(title)}" '
        'xmlns="http://www.w3.org/2000/svg" '
        'style="width:100%;height:auto;display:block">'
        f"<title>{escape(title)}</title>"
        f"<desc>{escape(desc) if desc else escape(title)}</desc>" + "".join(parts) + "</svg>"
    )


__all__ = [
    "BarPoint",
    "PieSlice",
    "svg_bar",
    "svg_pie",
]
