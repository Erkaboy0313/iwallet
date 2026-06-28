"""Write-side helpers for the daily quote feature."""

from __future__ import annotations

from accounts.models import User

from .models import QuoteDismissal

SESSION_HIDE_TODAY = "iw_quote_hidden_today"


def dismiss_forever(user: User) -> None:
    """Opt the user out of the daily quote until they re-enable from Settings."""
    QuoteDismissal.objects.get_or_create(user=user)


def reenable(user: User) -> None:
    """Reverse a `dismiss_forever` from the Settings hub toggle."""
    QuoteDismissal.objects.filter(user=user).delete()
