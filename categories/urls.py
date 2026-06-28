"""categories/urls.py — Epic 3 routes for CRUD + picker."""

from django.urls import path

from . import views

app_name = "categories"

urlpatterns = [
    path(
        "settings/categories/",
        views.category_list_view,
        name="list",
    ),
    path(
        "settings/categories/new/",
        views.category_create_view,
        name="create",
    ),
    path(
        "settings/categories/<int:category_id>/edit/",
        views.category_edit_view,
        name="edit",
    ),
    path(
        "settings/categories/<int:category_id>/delete/",
        views.category_delete_view,
        name="delete",
    ),
    path(
        "settings/categories/<int:category_id>/toggle-hide/",
        views.category_toggle_hide_view,
        name="toggle_hide",
    ),
    path(
        "categories/picker/",
        views.category_picker_view,
        name="picker",
    ),
]
