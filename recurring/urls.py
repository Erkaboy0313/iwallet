"""recurring/urls.py — Epic 7 / Story 7.2 settings routes."""

from django.urls import path

from . import views

app_name = "recurring"

urlpatterns = [
    path(
        "settings/recurring/",
        views.recurring_list_view,
        name="list",
    ),
    path(
        "settings/recurring/new/",
        views.recurring_create_view,
        name="create",
    ),
    path(
        "settings/recurring/<int:schedule_id>/edit/",
        views.recurring_edit_view,
        name="edit",
    ),
    path(
        "settings/recurring/<int:schedule_id>/delete/",
        views.recurring_delete_view,
        name="delete",
    ),
    path(
        "settings/recurring/<int:schedule_id>/toggle/",
        views.recurring_toggle_view,
        name="toggle",
    ),
    path(
        "recurring/<int:schedule_id>/prompt/confirm/",
        views.prompt_confirm_view,
        name="prompt_confirm",
    ),
    path(
        "recurring/<int:schedule_id>/prompt/skip/",
        views.prompt_skip_view,
        name="prompt_skip",
    ),
    path(
        "recurring/<int:schedule_id>/prompt/defer/",
        views.prompt_defer_view,
        name="prompt_defer",
    ),
]
