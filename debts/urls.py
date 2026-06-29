"""debts/urls.py — v0.7 simplified: Qarzlar = filtered Transactions list."""

from django.urls import path

from . import views

app_name = "debts"

urlpatterns = [
    path("debts/", views.debts_list_view, name="list"),
]
