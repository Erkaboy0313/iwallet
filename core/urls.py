"""core/urls.py — Home shell + auth'd content endpoint."""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("home/", views.home, name="home"),
    path("home/content/", views.home_content, name="home_content"),
    path("settings/", views.settings_hub, name="settings_hub"),
    path("settings/quote-toggle/", views.toggle_quote_feature, name="toggle_quote_feature"),
]
