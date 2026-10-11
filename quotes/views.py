"""Quote endpoints: per-session hide + permanent dismiss."""

from __future__ import annotations

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from .services import SESSION_HIDE_TODAY, dismiss_forever


@require_POST
def hide_today(request) -> HttpResponse:
    """Hide the quote for the current WebApp session only.

    An empty 200 response lets htmx replace the card with nothing.
    A 204 response skips swapping and leaves the dismissed card visible.
    """
    request.session[SESSION_HIDE_TODAY] = True
    return HttpResponse("")


@require_POST
def dismiss(request) -> HttpResponse:
    """Permanently opt out — also records a QuoteDismissal row."""
    dismiss_forever(request.user)
    request.session[SESSION_HIDE_TODAY] = True
    return HttpResponse(status=204)
