"""debts/urls.py — v0.7 simplified routes."""

from django.urls import path

from . import views

app_name = "debts"

urlpatterns = [
    path("debts/", views.debts_list_view, name="list"),
    path("debts/new/", views.new_debt_view, name="new"),
    path("debts/<int:tx_id>/settle/", views.settle_debt_view, name="settle"),
]
