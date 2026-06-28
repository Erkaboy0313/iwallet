"""Category CRUD + picker views (Epic 3 — Stories 3.1, 3.2)."""

import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .exceptions import (
    CannotEditPresetError,
    DuplicateCategoryError,
    InvalidCategoryNameError,
)
from .forms import CategoryForm
from .models import Category, CategoryType
from .selectors import categories_for, categories_for_settings
from .services import create_category, delete_category, toggle_hide_preset, update_category


def _list_context(user) -> dict:
    return {
        "income_categories": categories_for_settings(user, CategoryType.INCOME.value),
        "expense_categories": categories_for_settings(user, CategoryType.EXPENSE.value),
    }


def _toast(message: str, type_: str = "success") -> str:
    return json.dumps({"toast": {"type": type_, "message": message}})


# ---------- Settings list (Story 3.1) ----------


@require_GET
def category_list_view(request):
    """Render `/app/settings/categories/` — the management page."""
    context = _list_context(request.user)
    template = (
        "categories/_list_partial.html"
        if request.headers.get("HX-Request") == "true"
        else "categories/list.html"
    )
    return render(request, template, context)


# ---------- Create custom (Story 3.1) ----------


@require_http_methods(["GET", "POST"])
def category_create_view(request):
    """Bottom-sheet form: GET returns the form partial; POST creates the row."""
    initial_type = request.GET.get("type") or CategoryType.EXPENSE.value

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                create_category(
                    user=request.user,
                    type_=form.cleaned_data["type"],
                    name=form.cleaned_data["name"],
                    emoji=form.cleaned_data["emoji"],
                )
            except (DuplicateCategoryError, InvalidCategoryNameError) as exc:
                form.add_error("name", str(exc))
                return _form_error_response(request, form, action_url=request.path)
            return _list_swap_response(request, "Kategoriya qo'shildi.")
        return _form_error_response(request, form, action_url=request.path)

    form = CategoryForm(initial={"type": initial_type, "emoji": "📌"})
    return render(
        request,
        "categories/_form.html",
        {"form": form, "action_url": request.path, "mode": "create"},
    )


# ---------- Edit custom (Story 3.1) ----------


@require_http_methods(["GET", "POST"])
def category_edit_view(request, category_id: int):
    category = get_object_or_404(
        Category.objects.filter(user=request.user),
        pk=category_id,
    )

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                update_category(
                    category=category,
                    name=form.cleaned_data["name"],
                    emoji=form.cleaned_data["emoji"],
                    type_=form.cleaned_data["type"],
                )
            except (
                DuplicateCategoryError,
                InvalidCategoryNameError,
                CannotEditPresetError,
            ) as exc:
                form.add_error("name", str(exc))
                return _form_error_response(request, form, action_url=request.path)
            return _list_swap_response(request, "Kategoriya yangilandi.")
        return _form_error_response(request, form, action_url=request.path)

    form = CategoryForm(
        initial={
            "type": category.type,
            "name": category.name,
            "emoji": category.emoji,
        }
    )
    return render(
        request,
        "categories/_form.html",
        {
            "form": form,
            "action_url": request.path,
            "mode": "edit",
            "category": category,
        },
    )


# ---------- Delete custom (Story 3.1) ----------


@require_http_methods(["GET", "POST"])
def category_delete_view(request, category_id: int):
    """GET returns the confirmation modal; POST migrates txs + deletes the row."""
    category = get_object_or_404(
        Category.objects.filter(user=request.user),
        pk=category_id,
    )

    if request.method == "POST":
        try:
            delete_category(category=category)
        except CannotEditPresetError as exc:
            return HttpResponse(str(exc), status=422)
        return _list_swap_response(
            request,
            "Kategoriya o'chirildi. Tegishli tranzaksiyalar 'Boshqa' ga ko'chirildi.",
        )

    return render(
        request,
        "categories/_confirm_delete.html",
        {"category": category, "action_url": request.path},
    )


# ---------- Hide / Show preset (Story 3.1) ----------


@require_POST
def category_toggle_hide_view(request, category_id: int):
    category = get_object_or_404(Category, pk=category_id, user__isnull=True)
    is_hidden_now = toggle_hide_preset(user=request.user, category=category)
    message = "Kategoriya yashirildi." if is_hidden_now else "Kategoriya ko'rsatildi."
    return _list_swap_response(request, message)


# ---------- Picker (Story 3.2) ----------


@require_GET
def category_picker_view(request):
    """Render the bottom-sheet picker as an htmx partial.

    Caller passes `?type=income|expense` and an optional `?target=<input-id>`
    so Alpine on the picker can write the picked slug into the right field.
    """
    type_ = request.GET.get("type") or CategoryType.EXPENSE.value
    target = request.GET.get("target") or "id_category_slug"
    if type_ not in {CategoryType.INCOME.value, CategoryType.EXPENSE.value}:
        type_ = CategoryType.EXPENSE.value
    categories = list(categories_for(request.user, type_))
    # Force "Boshqa" to render last regardless of frequency ordering (AC 3.2).
    categories.sort(key=lambda c: (c.slug == "boshqa", -c.usage_count, c.name))
    return render(
        request,
        "categories/_picker.html",
        {"categories": categories, "type": type_, "target_field": target},
    )


# ---------- helpers ----------


def _list_swap_response(request, message: str) -> HttpResponse:
    """After a successful mutation: re-render the list partial + flash toast."""
    response = render(request, "categories/_list_partial.html", _list_context(request.user))
    response.headers["HX-Trigger"] = _toast(message)
    response.headers["HX-Retarget"] = "#category-list"
    response.headers["HX-Reswap"] = "outerHTML"
    return response


def _form_error_response(request, form, *, action_url: str) -> HttpResponse:
    response = render(
        request,
        "categories/_form.html",
        {"form": form, "action_url": action_url, "mode": "create"},
    )
    response.status_code = 422
    return response
