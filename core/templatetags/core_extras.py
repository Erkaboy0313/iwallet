"""Template filters for the IWALLET frontend.

Smart money formatting — full digits, thin-space groups, compact currency
symbol. Eric's call (v0.7 follow-up): "1000 som ham muhim" — never round.
"""

from decimal import Decimal

from django import template

from currencies.constants import (
    currency_label as _currency_label,
    currency_symbol as _currency_symbol,
)

register = template.Library()


@register.filter(name="currency_label")
def currency_label(code: str) -> str:
    """Render the Uzbek label for a currency code (so'm/rubl/dollar)."""
    return _currency_label(code or "")


@register.filter(name="currency_symbol")
def currency_symbol(code: str) -> str:
    """Render the compact glyph for a currency code (so'm / $ / ₽)."""
    return _currency_symbol(code or "")


THIN_SPACE = " "


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
    """Render an amount with thin-space digit groups + compact currency symbol.

    Never rounds — every som matters. Examples:
      25000 UZS    -> "25 000 so'm"
      1250000 UZS  -> "1 250 000 so'm"
      0 UZS        -> "0 so'm"
      1500.50 USD  -> "1 500.50 $"
    """
    if value is None:
        return ""
    try:
        amount = Decimal(value)
    except (TypeError, ValueError):
        return str(value)

    symbol = _currency_symbol(currency)

    whole_part = int(amount) if amount == int(amount) else None
    if whole_part is not None:
        return f"{whole_part:,}".replace(",", THIN_SPACE) + f" {symbol}"
    # Has cents — render with comma + 2 decimals, swap commas for thin space.
    formatted = f"{amount:,.2f}".replace(",", THIN_SPACE)
    return f"{formatted} {symbol}"
