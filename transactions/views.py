"""Manual transaction entry + history + edit + delete views (Story 1.4 + 1.6)."""

import json
from datetime import date as _date_today

from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .exceptions import RestoreExpiredError
from .forms import ManualTransactionForm
from .models import Transaction
from .selectors import history_list
from .services import (
    create_transaction,
    restore_transaction,
    soft_delete_transaction,
    update_transaction,
)

HISTORY_PAGE_SIZE = 20

# (value, label) — value="" matches the "Hammasi" pill (no filter).
HISTORY_FILTER_CHOICES = [
    ("", "Hammasi"),
    ("income", "Kirim"),
    ("expense", "Chiqim"),
    ("debt_lent", "Qarz berdim"),
    ("debt_borrowed", "Qarz oldim"),
]


@require_http_methods(["GET", "POST"])
def add_transaction_view(request):
    """Render the manual entry form (GET) or persist + redirect (POST)."""
    if request.method == "POST":
        form = ManualTransactionForm(request.POST, user=request.user)
        if form.is_valid():
            tx = create_transaction(
                user=request.user,
                type=form.cleaned_data["type"],
                amount=form.cleaned_data["amount"],
                currency=form.cleaned_data["currency"],
                date=form.cleaned_data["date"],
                category=form.cleaned_data.get("category"),
                counterparty=form.cleaned_data.get("counterparty", ""),
                note=form.cleaned_data.get("note", ""),
            )
            return _success_response(tx)
        return _invalid_form_response(request, form)

    form = ManualTransactionForm(
        initial={"date": _date_today.today(), "currency": "UZS"},
        user=request.user,
    )
    return render(request, "transactions/add.html", {"form": form})


def _success_response(_tx) -> HttpResponse:
    """htmx response: navigate home + flash a toast."""
    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("core:home")
    response.headers["HX-Trigger"] = json.dumps(
        {"toast": {"type": "success", "message": "Tranzaksiya saqlandi"}}
    )
    return response


def _invalid_form_response(request, form) -> HttpResponse:
    """422 keeps semantics meaningful while still letting htmx swap the form."""
    response = render(request, "transactions/add.html", {"form": form})
    response.status_code = 422
    return response


# ---------- History (Story 1.6) ----------


@require_GET
def history_view(request):
    """List the user's transactions with optional filters.

    htmx requests receive just the list partial so the chrome (filter pills,
    page title) stays put when a filter pill is tapped.
    """
    type_ = request.GET.get("type") or None
    currency = request.GET.get("currency") or None

    qs = history_list(request.user, type_=type_, currency=currency)
    page_number = request.GET.get("page") or 1
    paginator = Paginator(qs, HISTORY_PAGE_SIZE)
    page = paginator.get_page(page_number)

    context = {
        "page": page,
        "filter_type": type_,
        "filter_currency": currency,
        "filter_choices": HISTORY_FILTER_CHOICES,
        "any_filter_active": bool(type_ or currency),
    }
    template = (
        "transactions/_history_list.html"
        if request.headers.get("HX-Request")
        else "transactions/history.html"
    )
    return render(request, template, context)


@require_GET
def transaction_detail_view(request, tx_id: int):
    """Read-only detail view. Edit / O'chirish actions live on this page."""
    tx = get_object_or_404(
        Transaction.objects.for_user(request.user).select_related("category"),
        pk=tx_id,
    )
    return render(request, "transactions/detail.html", {"tx": tx})


@require_http_methods(["GET", "POST"])
def edit_transaction_view(request, tx_id: int):
    """Edit an existing live transaction (not soft-deleted)."""
    tx = get_object_or_404(
        Transaction.objects.for_user(request.user),
        pk=tx_id,
    )

    if request.method == "POST":
        form = ManualTransactionForm(request.POST, user=request.user)
        if form.is_valid():
            update_transaction(
                tx=tx,
                type=form.cleaned_data["type"],
                amount=form.cleaned_data["amount"],
                currency=form.cleaned_data["currency"],
                date=form.cleaned_data["date"],
                category=form.cleaned_data.get("category"),
                counterparty=form.cleaned_data.get("counterparty", ""),
                note=form.cleaned_data.get("note", ""),
            )
            response = HttpResponse(status=200)
            response.headers["HX-Redirect"] = reverse("transactions:detail", args=[tx.id])
            response.headers["HX-Trigger"] = json.dumps(
                {"toast": {"type": "success", "message": "Tranzaksiya yangilandi"}}
            )
            return response
        response = render(request, "transactions/edit.html", {"form": form, "tx": tx})
        response.status_code = 422
        return response

    initial = {
        "type": tx.type,
        "amount": tx.amount,
        "currency": tx.currency,
        "date": tx.date,
        "note": tx.note,
        "counterparty": tx.counterparty,
        "category_slug": tx.category.slug if tx.category else "",
    }
    form = ManualTransactionForm(initial=initial, user=request.user)
    return render(request, "transactions/edit.html", {"form": form, "tx": tx})


@require_POST
def delete_transaction_view(request, tx_id: int):
    """Soft-delete a transaction; htmx redirects to history + flash an info toast."""
    tx = get_object_or_404(
        Transaction.objects.for_user(request.user),
        pk=tx_id,
    )
    soft_delete_transaction(tx=tx)
    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("transactions:history")
    response.headers["HX-Trigger"] = json.dumps(
        {
            "toast": {
                "type": "info",
                "message": "Tranzaksiya o'chirildi. 7 kun ichida tiklash mumkin.",
            }
        }
    )
    return response


@require_POST
def restore_transaction_view(request, tx_id: int):
    """Bring a soft-deleted transaction back inside the 7-day window."""
    tx = get_object_or_404(
        Transaction.objects.filter(user=request.user),
        pk=tx_id,
    )
    if not tx.is_deleted:
        raise Http404("Transaction is not deleted.")
    try:
        restore_transaction(tx=tx)
    except RestoreExpiredError:
        response = HttpResponse(status=410)
        response.headers["HX-Trigger"] = json.dumps(
            {"toast": {"type": "error", "message": "Tiklash muddati tugadi (7 kun)."}}
        )
        return response

    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("transactions:history")
    response.headers["HX-Trigger"] = json.dumps(
        {"toast": {"type": "success", "message": "Tranzaksiya tiklandi"}}
    )
    return response
