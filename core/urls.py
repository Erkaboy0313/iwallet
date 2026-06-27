"""core/urls.py — Home placeholder routes."""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("home/", views.home, name="home"),
]
