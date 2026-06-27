"""accounts/urls.py — Telegram auth + first-run onboarding routes."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Public shell (in PUBLIC_APP_PATHS) — renders the 3-card carousel.
    path("onboarding/", views.onboarding_view, name="onboarding"),
    # Auth-required completion endpoint — marks user.onboarded_at + HX-Redirect to home.
    path("me/onboarding/complete/", views.onboarding_complete_view, name="onboarding_complete"),
]
