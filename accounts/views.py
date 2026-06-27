"""Accounts views — onboarding (public shell + auth'd completion endpoint)."""

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .services import mark_onboarded


@require_GET
def onboarding_view(request):
    """Render the 3-card first-run onboarding.

    Public — anonymous OK. Telegram WebApp can't attach initData on the initial
    GET; the page itself is a shell. The "Boshlash" CTA hits
    `onboarding_complete_view` via htmx with the initData header injected by
    base.html's JS hook.
    """
    return render(request, "accounts/onboarding.html")


@require_POST
def onboarding_complete_view(request):
    """Mark the user as onboarded; htmx redirects to Home."""
    mark_onboarded(request.user)
    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("core:home")
    return response
