"""voice/urls.py — Epic 2 routes for the voice transaction pipeline."""

from django.urls import path

from . import views

app_name = "voice"

urlpatterns = [
    path("voice/transcribe/", views.transcribe, name="transcribe"),
    path("voice/save/", views.save, name="save"),
    path("voice/save-multi/", views.save_multi, name="save_multi"),
]
