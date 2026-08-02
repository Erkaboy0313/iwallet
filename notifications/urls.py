"""User-facing support routes (WebApp side of the admin chat relay)."""

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("support/", views.support_page_view, name="support"),
    path("support/send/", views.support_send_view, name="support_send"),
]
