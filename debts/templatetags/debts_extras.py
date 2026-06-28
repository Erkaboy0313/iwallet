"""Template filters for the Debts screens (Stories 4.3 / 4.4)."""

from django import template

from debts.selectors import initials_for

register = template.Library()


@register.filter(name="initials")
def initials(value) -> str:
    """Two-letter avatar initials for the counterparty name."""
    return initials_for(str(value or ""))
