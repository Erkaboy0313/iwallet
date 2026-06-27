"""Home shell + auth'd content endpoint (Story 1.5).

Two-phase render keeps the first GET cheap and public — Telegram WebApp can't
attach initData on the initial page load — while delegating per-user data to
an htmx-driven follow-up call that the middleware authenticates.
"""

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from transactions.selectors import month_summary


@require_GET
def home(request):
    """Render the public shell. JS in base.html injects initData on the htmx call."""
    return render(request, "core/home.html")


@require_GET
def home_content(request):
    """Auth-required: returns BalanceHero content OR an htmx redirect to onboarding."""
    user = request.user
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


@require_GET
def healthz(_request):
    """Anonymous healthcheck endpoint (Caddy + GitHub Actions deploy smoke test)."""
    return HttpResponse("ok", content_type="text/plain")
