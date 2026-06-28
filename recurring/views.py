"""Recurring CRUD views (Epic 7 / Story 7.2).

Lives at /app/settings/recurring/. The list view renders a `RecurringCard`
per schedule + an empty-state CTA when none exist. Create/edit use a
bottom-sheet form swapped in by htmx, mirroring the categories pattern
(Story 3.1).
"""

from __future__ import annotations

import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_POST

from categories.models import Category, CategoryType
from categories.selectors import categories_for, match_slug
from recurring.exceptions import (
    InvalidAmountError,
    InvalidNameError,
    InvalidScheduleError,
)
from recurring.forms import RecurringForm
from recurring.models import RecurringSchedule, RecurringType, ScheduleKind
from recurring.selectors import schedules_for
from recurring.services import (
    create_recurring,
    delete_recurring,
    pause_recurring,
    resume_recurring,
    update_recurring,
)


def _list_context(user) -> dict:
    return {"schedules": list(schedules_for(user))}


def _toast(message: str, type_: str = "success") -> str:
    return json.dumps({"toast": {"type": type_, "message": message}})


def _category_choices(user) -> dict:
    """Categories the picker can offer per type (income/expense).

    Recurring debt_lent/debt_borrowed don't get a picker (debts are tracked
    elsewhere); we still let the user save those with no category attached.
    """
    return {
        "income_categories": list(categories_for(user, CategoryType.INCOME.value)),
        "expense_categories": list(categories_for(user, CategoryType.EXPENSE.value)),
    }


def _resolve_category(user, *, type_: str, slug: str | None) -> Category | None:
    """Look up the picked category by slug, scoped to the right type.

    Debt types don't have categories so we always return None there.
    """
    if not slug or type_ in {RecurringType.DEBT_LENT.value, RecurringType.DEBT_BORROWED.value}:
        return None
    cat_type = (
        CategoryType.INCOME.value
        if type_ == RecurringType.INCOME.value
        else CategoryType.EXPENSE.value
    )
    return match_slug(user, slug=slug, type=cat_type)


# ---------- Settings list ----------


@require_http_methods(["GET"])
def recurring_list_view(request):
    """Render `/app/settings/recurring/` — the management page."""
    context = _list_context(request.user)
    template = (
        "recurring/_list_partial.html"
        if request.headers.get("HX-Request") == "true"
        else "recurring/list.html"
    )
    return render(request, template, context)


# ---------- Create ----------


@require_http_methods(["GET", "POST"])
def recurring_create_view(request):
    """Bottom-sheet form: GET → form partial, POST → create + swap list."""
    if request.method == "POST":
        form = RecurringForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            try:
                create_recurring(
                    user=request.user,
                    type_=cleaned["type"],
                    name=cleaned["name"],
                    amount=cleaned["amount"],
                    currency=cleaned["currency"],
                    category=_resolve_category(
                        request.user,
                        type_=cleaned["type"],
                        slug=cleaned.get("category_slug"),
                    ),
                    schedule_kind=cleaned["schedule_kind"],
                    day_of_month=cleaned.get("day_of_month"),
                    day_of_week=cleaned.get("day_of_week"),
                    end_date=cleaned.get("end_date"),
                )
            except (
                InvalidAmountError,
                InvalidNameError,
                InvalidScheduleError,
            ) as exc:
                form.add_error(None, str(exc))
                return _form_error_response(request, form, action_url=request.path)
            return _list_swap_response(request, "Takrorlanuvchi qo'shildi.")
        return _form_error_response(request, form, action_url=request.path)

    form = RecurringForm(
        initial={
            "type": RecurringType.EXPENSE.value,
            "currency": request.user.default_currency or "UZS",
            "schedule_kind": ScheduleKind.MONTHLY.value,
            "day_of_month": 1,
        }
    )
    context = {
        "form": form,
        "action_url": request.path,
        "mode": "create",
        **_category_choices(request.user),
    }
    return render(request, "recurring/_form.html", context)


# ---------- Edit ----------


@require_http_methods(["GET", "POST"])
def recurring_edit_view(request, schedule_id: int):
    schedule = get_object_or_404(
        RecurringSchedule.objects.filter(user=request.user),
        pk=schedule_id,
    )

    if request.method == "POST":
        form = RecurringForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            try:
                update_recurring(
                    schedule=schedule,
                    name=cleaned["name"],
                    amount=cleaned["amount"],
                    currency=cleaned["currency"],
                    type_=cleaned["type"],
                    schedule_kind=cleaned["schedule_kind"],
                    day_of_month=cleaned.get("day_of_month"),
                    day_of_week=cleaned.get("day_of_week"),
                    category=_resolve_category(
                        request.user,
                        type_=cleaned["type"],
                        slug=cleaned.get("category_slug"),
                    ),
                    end_date=cleaned.get("end_date"),
                )
            except (
                InvalidAmountError,
                InvalidNameError,
                InvalidScheduleError,
            ) as exc:
                form.add_error(None, str(exc))
                return _form_error_response(request, form, action_url=request.path)
            return _list_swap_response(request, "Takrorlanuvchi yangilandi.")
        return _form_error_response(request, form, action_url=request.path)

    initial = {
        "type": schedule.type,
        "name": schedule.name,
        "amount": str(schedule.amount.normalize()),
        "currency": schedule.currency,
        "schedule_kind": schedule.schedule_kind,
        "day_of_month": schedule.day_of_month,
        "day_of_week": "" if schedule.day_of_week is None else str(schedule.day_of_week),
        "end_date": schedule.end_date,
        "category_slug": schedule.category.slug if schedule.category else "",
    }
    form = RecurringForm(initial=initial)
    context = {
        "form": form,
        "action_url": request.path,
        "mode": "edit",
        "schedule": schedule,
        **_category_choices(request.user),
    }
    return render(request, "recurring/_form.html", context)


# ---------- Delete ----------


@require_http_methods(["GET", "POST"])
def recurring_delete_view(request, schedule_id: int):
    """GET → confirmation modal; POST → delete + list swap."""
    schedule = get_object_or_404(
        RecurringSchedule.objects.filter(user=request.user),
        pk=schedule_id,
    )

    if request.method == "POST":
        delete_recurring(schedule=schedule)
        return _list_swap_response(request, "Takrorlanuvchi o'chirildi.")

    return render(
        request,
        "recurring/_confirm_delete.html",
        {"schedule": schedule, "action_url": request.path},
    )


# ---------- Toggle active ----------


@require_POST
def recurring_toggle_view(request, schedule_id: int):
    schedule = get_object_or_404(
        RecurringSchedule.objects.filter(user=request.user),
        pk=schedule_id,
    )
    if schedule.is_active:
        pause_recurring(schedule=schedule)
        msg = "Takrorlanuvchi to'xtatildi."
    else:
        resume_recurring(schedule=schedule)
        msg = "Takrorlanuvchi qayta yoqildi."
    return _list_swap_response(request, msg)


# ---------- helpers ----------


def _list_swap_response(request, message: str) -> HttpResponse:
    """After a successful mutation: re-render the list partial + flash toast."""
    response = render(request, "recurring/_list_partial.html", _list_context(request.user))
    response.headers["HX-Trigger"] = _toast(message)
    response.headers["HX-Retarget"] = "#recurring-list"
    response.headers["HX-Reswap"] = "outerHTML"
    return response


def _form_error_response(request, form, *, action_url: str) -> HttpResponse:
    response = render(
        request,
        "recurring/_form.html",
        {
            "form": form,
            "action_url": action_url,
            "mode": "create",
            **_category_choices(request.user),
        },
    )
    response.status_code = 422
    return response
