"""Sprint 0 — placeholder Home view. Filled out in Story 1.5 (BalanceHero)."""

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    """Render the Home placeholder. Auth enforced by TelegramAuthMiddleware."""
    return render(request, "core/home.html", {"user": request.user})


@require_GET
def healthz(_request):
    """Anonymous healthcheck endpoint (Caddy + GitHub Actions deploy smoke test)."""
    return HttpResponse("ok", content_type="text/plain")
