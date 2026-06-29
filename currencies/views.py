"""Currency switcher endpoint.

POSTing here persists the user's display preference for the Home balance hero
(only). Transactions, history, and reports always stay in their source
currency — switching currency only flips the aggregated balance display.
"""

from __future__ import annotations

import logging

from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from currencies.constants import CURRENCY_CODES

logger = logging.getLogger(__name__)

SESSION_DISPLAY_CURRENCY = "iw_display_currency"
SESSION_STALE_BANNER_DISMISSED = "iw_stale_banner_dismissed_for"


@require_POST
def switch_display(request):
    """Persist the user's balance-display currency + re-trigger a home swap.

    Only `display_currency` is meaningful — everything else (transactions,
    history, reports) stays in source currency. The selection lives in the
    session; it does NOT touch `user.default_currency` (that's the source
    currency for new transactions and stays under Settings control).
    """
    currency = (request.POST.get("display_currency") or "").upper()
    if currency and currency in CURRENCY_CODES:
        request.session[SESSION_DISPLAY_CURRENCY] = currency
        request.session.pop(SESSION_STALE_BANNER_DISMISSED, None)

    response = HttpResponse(status=204)
    response.headers["HX-Redirect"] = reverse("core:home")
    return response
