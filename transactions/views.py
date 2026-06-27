"""Manual transaction entry view (Story 1.4)."""

import json
from datetime import date as _date_today

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import ManualTransactionForm
from .services import create_transaction


@require_http_methods(["GET", "POST"])
def add_transaction_view(request):
    """Render the manual entry form (GET) or persist + redirect (POST).

    Auth enforced by TelegramAuthMiddleware (this path is NOT in PUBLIC_APP_PATHS).
    Returns 422 with the form re-rendered on validation failure so htmx swaps the
    error markup into place.
    """
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
