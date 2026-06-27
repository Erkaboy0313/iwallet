"""Sprint 0 — placeholder Home view. Filled out in Story 1.5 (BalanceHero)."""

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    """Render the Home placeholder shell. Anonymous-OK (in PUBLIC_APP_PATHS).

    Telegram WebApp can't attach initData on the first page GET; the SDK provides
    user info via `Telegram.WebApp.initDataUnsafe` to JS after load. Real per-user
    endpoints (Story 1.5+) will live behind the middleware and use htmx-injected
    `X-Telegram-InitData` headers.
    """
    return render(request, "core/home.html")


@require_GET
def healthz(_request):
    """Anonymous healthcheck endpoint (Caddy + GitHub Actions deploy smoke test)."""
    return HttpResponse("ok", content_type="text/plain")
