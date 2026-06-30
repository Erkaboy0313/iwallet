"""Recurring CRUD + prompt resolution views.

The list lives at /app/settings/recurring/. Create/edit render as full-page
forms (matching the Add Transaction page) so the form scrolls naturally and
can reuse the modal category picker.

Prompt resolution endpoints (confirm/skip/defer) are POST-only and called
from the home page's "Bugun" prompt cards via htmx.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
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
    confirm_prompt,
    create_recurring,
    defer_prompt,
    delete_recurring,
    pause_recurring,
    resume_recurring,
    skip_prompt,
    update_recurring,
)


def _list_context(user) -> dict:
    return {"schedules": list(schedules_for(user))}


def _category_choices(user) -> dict:
    return {
        "income_categories": list(categories_for(user, CategoryType.INCOME.value)),
        "expense_categories": list(categories_for(user, CategoryType.EXPENSE.value)),
    }


def _resolve_category(user, *, type_: str, slug: str | None) -> Category | None:
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
                return _render_form(request, form, mode="create", status=422)
            return redirect("recurring:list")
        return _render_form(request, form, mode="create", status=422)

    form = RecurringForm(
        initial={
            "type": RecurringType.EXPENSE.value,
            "currency": request.user.default_currency or "UZS",
            "schedule_kind": ScheduleKind.MONTHLY.value,
            "day_of_month": 1,
        }
    )
    return _render_form(request, form, mode="create")


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
                return _render_form(request, form, mode="edit", schedule=schedule, status=422)
            return redirect("recurring:list")
        return _render_form(request, form, mode="edit", schedule=schedule, status=422)

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
    return _render_form(request, form, mode="edit", schedule=schedule)


# ---------- Delete ----------


@require_http_methods(["GET", "POST"])
def recurring_delete_view(request, schedule_id: int):
    schedule = get_object_or_404(
        RecurringSchedule.objects.filter(user=request.user),
        pk=schedule_id,
    )
    if request.method == "POST":
        delete_recurring(schedule=schedule)
        return redirect("recurring:list")
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
    else:
        resume_recurring(schedule=schedule)
    return _list_swap_response(request)


# ---------- Prompt resolution ----------


@require_POST
def prompt_confirm_view(request, schedule_id: int):
    """User said Ha on a Bugun prompt card. Optionally accepts edited amount."""
    schedule = get_object_or_404(
        RecurringSchedule.objects.filter(user=request.user),
        pk=schedule_id,
    )
    amount = _parse_amount(request.POST.get("amount"))
    save_amount = request.POST.get("save_amount") in {"on", "1", "true"}
    confirm_prompt(
        schedule=schedule,
        today=timezone.localdate(),
        amount=amount,
        save_amount=save_amount,
    )
    return _redirect_home_response(request)


@require_POST
def prompt_skip_view(request, schedule_id: int):
    """User said Yo'q. Advance cursor without a transaction."""
    schedule = get_object_or_404(
        RecurringSchedule.objects.filter(user=request.user),
        pk=schedule_id,
    )
    skip_prompt(schedule=schedule, today=timezone.localdate())
    return _redirect_home_response(request)


@require_POST
def prompt_defer_view(request, schedule_id: int):
    """User said Ertaga eslat. Hide this prompt until tomorrow."""
    schedule = get_object_or_404(
        RecurringSchedule.objects.filter(user=request.user),
        pk=schedule_id,
    )
    defer_prompt(schedule=schedule, today=timezone.localdate())
    return _redirect_home_response(request)


# ---------- helpers ----------


def _render_form(
    request,
    form: RecurringForm,
    *,
    mode: str,
    schedule: RecurringSchedule | None = None,
    status: int = 200,
) -> HttpResponse:
    action_url = (
        reverse("recurring:edit", args=[schedule.id])
        if schedule is not None
        else reverse("recurring:create")
    )
    context = {
        "form": form,
        "action_url": action_url,
        "mode": mode,
        "schedule": schedule,
        **_category_choices(request.user),
    }
    response = render(request, "recurring/_form.html", context)
    if status != 200:
        response.status_code = status
    return response


def _list_swap_response(request) -> HttpResponse:
    if request.headers.get("HX-Request") == "true":
        return render(request, "recurring/_list_partial.html", _list_context(request.user))
    return redirect("recurring:list")


def _redirect_home_response(request) -> HttpResponse:
    """After a prompt action: htmx requests get HX-Redirect, plain POSTs a 302."""
    if request.headers.get("HX-Request") == "true":
        response = HttpResponse(status=204)
        response.headers["HX-Refresh"] = "true"
        return response
    return redirect("core:home")


def _parse_amount(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    cleaned = raw.strip().replace(" ", "").replace(",", ".")
    if not cleaned:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return value
