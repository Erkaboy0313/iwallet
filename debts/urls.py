"""debts/urls.py — Epic 4 routes mounted under /app/ in iwallet.urls."""

from django.urls import path

from . import views

app_name = "debts"

urlpatterns = [
    path("debts/", views.debts_list_view, name="list"),
    path("debts/new/", views.debt_create_view, name="create"),
    path("debts/<int:debt_id>/", views.debt_detail_view, name="detail"),
    path("debts/<int:debt_id>/close/", views.debt_close_form_view, name="close_form"),
    path("debts/<int:debt_id>/repay/", views.debt_repay_view, name="repay"),
    path("debts/<int:debt_id>/cancel/", views.debt_cancel_view, name="cancel"),
]
