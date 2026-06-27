"""Home shell + auth-tolerant content endpoint (Story 1.5 + post-deploy fix).

Two-phase render: the shell at /app/home/ is public; /app/home/content/ is also
public but tries to authenticate via the X-Telegram-InitData header. Missing or
invalid initData falls back to an anonymous welcome card so the WebApp renders
under any Telegram launch context (Menu Button on Desktop can ship empty
initData; mobile + inline buttons are reliable).
"""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from accounts.exceptions import InvalidInitDataError
from accounts.services import get_or_create_user_from_init_data, validate_init_data
from transactions.selectors import month_summary

logger = logging.getLogger(__name__)
INIT_DATA_HEADER = "X-Telegram-InitData"


@require_GET
def home(request):
    """Render the public shell. JS in base.html attaches initData on the htmx call."""
    return render(request, "core/home.html")


@require_GET
def home_content(request):
    """Render BalanceHero if authed; otherwise an anonymous welcome fallback."""
    init_data = request.headers.get(INIT_DATA_HEADER, "")
    user = _try_authenticate(init_data)

    if user is None:
        return render(request, "core/_home_anonymous.html")

    if user.onboarded_at is None:
        response = HttpResponse(status=200)
        response.headers["HX-Redirect"] = reverse("accounts:onboarding")
        return response

    summary = month_summary(user, currency=user.default_currency)
    return render(
        request,
        "core/_balance_hero.html",
        {"summary": summary, "user": user},
    )


def _try_authenticate(init_data: str):
    """Best-effort: returns a User on success, None when initData is missing/invalid.

    Logs key signal (length + reason) without leaking the raw header so we can
    diagnose from server logs without exposing user data.
    """
    if not init_data:
        logger.info("home_content auth: init_data header empty")
        return None
    logger.info("home_content auth: received init_data length=%d", len(init_data))
    try:
        user_dict = validate_init_data(init_data, settings.TELEGRAM_BOT_TOKEN)
    except InvalidInitDataError as e:
        logger.info("home_content auth: validation failed reason=%s", e)
        return None
    logger.info("home_content auth: ok user_id=%s", user_dict.get("id"))
    return get_or_create_user_from_init_data(user_dict)


@require_GET
def healthz(_request):
    """Anonymous healthcheck endpoint (Caddy + GitHub Actions deploy smoke test)."""
    return HttpResponse("ok", content_type="text/plain")
