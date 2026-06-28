"""Template filters for the IWALLET frontend (Story 1.5+).

Smart money formatting per project-context.md / UX-DR22.
"""

from decimal import Decimal

from django import template

from currencies.constants import currency_label as _currency_label

register = template.Library()


@register.filter(name="currency_label")
def currency_label(code: str) -> str:
    """Render the Uzbek label for a currency code (so'm/rubl/dollar)."""
    return _currency_label(code or "")


THIN_SPACE = " "
ONE_MILLION = Decimal("1000000")


@register.simple_tag()
def sparkline_path(series, width: int = 100, height: int = 32) -> str:
    """Build an SVG <path d="..."> for an inline sparkline.

    series: iterable of DailyAmount or any object with an `amount` attribute.
    Returns the path command string ("M0,32 L7,18 …") — caller wraps in SVG.
    Empty / all-zero series collapses to a flat baseline.
    """
    values = [float(getattr(item, "amount", 0) or 0) for item in (series or [])]
    if not values:
        return ""
    peak = max(values) or 1.0
    n = len(values)
    step = width / max(n - 1, 1)
    coords = []
    for i, v in enumerate(values):
        x = i * step
        y = height - (v / peak) * (height - 2) - 1  # 1px top/bottom inset
        coords.append(f"{x:.1f},{y:.1f}")
    return "M" + " L".join(coords)


@register.filter(name="smart_money")
def smart_money(value, currency: str = "UZS") -> str:
    """Render an amount with thin-space groups + optional `mln` collapsing.

    Examples:
      25000 UZS  -> "25 000 UZS"
      1250000 UZS -> "1.25 mln UZS"
      0 UZS -> "0 UZS"
    """
    if value is None:
        return ""
    try:
        amount = Decimal(value)
    except (TypeError, ValueError):
        return str(value)

    if abs(amount) >= ONE_MILLION:
        mln = amount / ONE_MILLION
        formatted = f"{mln:.2f}".rstrip("0").rstrip(".")
        return f"{formatted} mln {currency}"

    # Drop trailing .00 then group thousands with a thin space.
    whole_part = int(amount) if amount == int(amount) else None
    if whole_part is not None:
        return f"{whole_part:,}".replace(",", THIN_SPACE) + f" {currency}"
    # Has cents — render with comma + 2 decimals, swap commas for thin space.
    formatted = f"{amount:,.2f}".replace(",", THIN_SPACE)
    return f"{formatted} {currency}"
