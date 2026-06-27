"""transactions/urls.py — manual entry routes (Story 1.4)."""

from django.urls import path

from . import views

app_name = "transactions"

urlpatterns = [
    path("transactions/add/", views.add_transaction_view, name="add"),
]
