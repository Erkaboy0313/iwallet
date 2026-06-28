"""reports/urls.py — weekly/monthly/yearly routes (Epic 8)."""

from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("reports/", views.weekly_view, name="index"),
    path("reports/weekly/", views.weekly_view, name="weekly"),
    path("reports/monthly/", views.monthly_view, name="monthly"),
    path("reports/yearly/", views.yearly_view, name="yearly"),
]
