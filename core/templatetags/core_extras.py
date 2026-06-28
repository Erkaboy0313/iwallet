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
