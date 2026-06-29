"""transactions/urls.py — manual entry routes (Story 1.4)."""

from django.urls import path

from . import views

app_name = "transactions"

urlpatterns = [
    path("transactions/add/", views.add_transaction_view, name="add"),
    path("transactions/history/", views.history_view, name="history"),
    path("transactions/<int:tx_id>/", views.transaction_detail_view, name="detail"),
    path("transactions/<int:tx_id>/edit/", views.edit_transaction_view, name="edit"),
    path("transactions/<int:tx_id>/delete/", views.delete_transaction_view, name="delete"),
    path("transactions/<int:tx_id>/restore/", views.restore_transaction_view, name="restore"),
]
