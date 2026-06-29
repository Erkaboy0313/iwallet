"""Currency choices + labels — single source of truth (Story 5.1).

All models, forms, and templates should import from here instead of duplicating
the tuple. The labels are Uzbek (mirroring `accounts.CURRENCY_CHOICES`, which
this module supersedes — that alias is kept for backwards compatibility).
"""

from __future__ import annotations

CURRENCY_UZS = "UZS"
CURRENCY_RUB = "RUB"
CURRENCY_USD = "USD"

CURRENCY_CHOICES: list[tuple[str, str]] = [
    (CURRENCY_UZS, "so'm"),
    (CURRENCY_RUB, "rubl"),
    (CURRENCY_USD, "dollar"),
]

CURRENCY_CODES: tuple[str, ...] = tuple(code for code, _ in CURRENCY_CHOICES)

# Mapping consumed by the `currency_label` template filter.
CURRENCY_LABELS: dict[str, str] = dict(CURRENCY_CHOICES)

# Compact glyphs used by `smart_money` so amounts read with less ink.
CURRENCY_SYMBOLS: dict[str, str] = {
    CURRENCY_UZS: "so'm",
    CURRENCY_USD: "$",
    CURRENCY_RUB: "₽",
}


def currency_label(code: str) -> str:
    """Return the human-friendly Uzbek label for a currency code.

    Falls back to the code itself if unknown so we don't blow up UI templates
    when a legacy row sneaks through.
    """
    return CURRENCY_LABELS.get(code, code)


def currency_symbol(code: str) -> str:
    """Return the compact glyph (so'm / $ / ₽) for a currency code."""
    return CURRENCY_SYMBOLS.get(code, code)
