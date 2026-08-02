"""WebApp-side views for user↔admin communication (support chat)."""

from __future__ import annotations

import json
import logging

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from .services import send_user_message_to_admin

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def support_page_view(request):
    """Render the support-chat form. User writes → admin receives via Telegram."""
    return render(request, "notifications/support.html")


@require_POST
def support_send_view(request):
    """Forward the user's text into the admin's Telegram DM.

    Admin's swipe-reply on that forwarded message routes back to the user's
    bot DM (see `_relay_admin_reply` in bot/handlers.py). So the reply lands
    in Telegram, not back in the WebApp — natural push-notification loop.
    """
    text = (request.POST.get("text") or "").strip()
    if not text:
        return _hx_response(400, "Xabar bo'sh", success=False)

    ok = send_user_message_to_admin(request.user, text)
    if not ok:
        return _hx_response(500, "Yuborilmadi. Yana urinib ko'ring.", success=False)

    response = _hx_response(
        200, "Xabaringiz yuborildi. Admin javob bersa botga xabar keladi.", success=True
    )
    response.headers["HX-Redirect"] = reverse("core:settings_hub")
    return response


def _hx_response(status: int, toast_message: str, *, success: bool) -> HttpResponse:
    response = HttpResponse(status=status)
    response.headers["HX-Trigger"] = json.dumps(
        {"toast": {"type": "success" if success else "error", "message": toast_message}},
    )
    return response
