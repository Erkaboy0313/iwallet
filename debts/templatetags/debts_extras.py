"""Template filters for the Debts screens (Stories 4.3 / 4.4 + v0.6 §6.3)."""

from django import template

from debts.selectors import initials_for

register = template.Library()


@register.filter(name="initials")
def initials(value) -> str:
    """Two-letter avatar initials for the counterparty name."""
    return initials_for(str(value or ""))


# 8 muted Tailwind 500-shade backgrounds + a white-on-X palette. The same
# counterparty name always maps to the same colour (deterministic hash).
_AVATAR_PALETTE = [
    ("#64748B", "#FFFFFF"),  # slate
    ("#10B981", "#FFFFFF"),  # emerald
    ("#D97706", "#FFFFFF"),  # amber-600
    ("#E11D48", "#FFFFFF"),  # rose
    ("#6366F1", "#FFFFFF"),  # indigo
    ("#0D9488", "#FFFFFF"),  # teal-600
    ("#9333EA", "#FFFFFF"),  # purple
    ("#0891B2", "#FFFFFF"),  # cyan-600
]


@register.simple_tag()
def avatar_style(name: str) -> str:
    """Return inline 'background: …; color: …' for a deterministic avatar."""
    bg, fg = _AVATAR_PALETTE[hash(name or "") % len(_AVATAR_PALETTE)]
    return f"background: {bg}; color: {fg}"
