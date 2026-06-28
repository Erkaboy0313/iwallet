"""Currency switcher endpoint (Story 5.5).

POSTing here persists the user's display preference (currency + raw/converted
mode). htmx redirects the BalanceHero swap after persistence so the home view
re-renders with the new mode.
"""

from __future__ import annotations

import logging

from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from currencies.constants import CURRENCY_CODES

logger = logging.getLogger(__name__)

DISPLAY_MODE_RAW = "raw"
DISPLAY_MODE_CONVERTED = "converted"
DISPLAY_MODES = (DISPLAY_MODE_RAW, DISPLAY_MODE_CONVERTED)

SESSION_DISPLAY_CURRENCY = "iw_display_currency"
SESSION_DISPLAY_MODE = "iw_display_mode"
SESSION_STALE_BANNER_DISMISSED = "iw_stale_banner_dismissed_for"


@require_POST
def switch_display(request):
    """Persist the user's display preference + re-trigger a home swap.

    Session-level for now (per Story 5.5 v1 — full DB persistence for the
    `User.show_converted` flag lands when Eric adds the Settings UI). We do
    still write to `User.show_converted` if the user is authed so the
    preference survives across sessions; the session entry is a fast cache
    that doesn't require a DB write on every render.
    """
    currency = (request.POST.get("display_currency") or "").upper()
    mode = (request.POST.get("display_mode") or "").lower()

    if currency and currency in CURRENCY_CODES:
        request.session[SESSION_DISPLAY_CURRENCY] = currency
    if mode in DISPLAY_MODES:
        request.session[SESSION_DISPLAY_MODE] = mode

    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False) and mode in DISPLAY_MODES:
        user.show_converted = mode == DISPLAY_MODE_CONVERTED
        if currency and currency in CURRENCY_CODES:
            user.default_currency = currency
        user.save(update_fields=["show_converted", "default_currency"])

    # Reset any prior stale-banner dismissal — a real preference change deserves
    # a fresh chance to warn the user.
    request.session.pop(SESSION_STALE_BANNER_DISMISSED, None)

    response = HttpResponse(status=204)
    response.headers["HX-Redirect"] = reverse("core:home_content")
    return response
