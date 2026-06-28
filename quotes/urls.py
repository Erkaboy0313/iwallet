"""quotes/urls.py — hide-today + permanent dismiss."""

from django.urls import path

from . import views

app_name = "quotes"

urlpatterns = [
    path("me/quote/hide/", views.hide_today, name="hide_today"),
    path("me/quote/dismiss/", views.dismiss, name="dismiss"),
]
