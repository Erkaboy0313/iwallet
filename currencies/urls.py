"""currencies/urls.py — display preference + (future) switcher endpoints."""

from django.urls import path

from . import views

app_name = "currencies"

urlpatterns = [
    path("settings/display/", views.switch_display, name="switch_display"),
]
