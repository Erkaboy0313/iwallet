"""Debt screens (Stories 4.3, 4.4) — list, create, close form, repay, cancel.

All views are auth-gated by TelegramAuthMiddleware. Per project-context, this
module only orchestrates: persistence and state transitions live in
`debts.services`, queries live in `debts.selectors`.
"""

from __future__ import annotations

import json
from datetime import datetime, time

from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .exceptions import (
    CurrencyMismatchError,
    DebtAlreadyClosedError,
    InvalidDebtAmountError,
    RepaymentExceedsRemainingError,
)
from .forms import DebtCreateForm, DebtRepayForm
from .models import DebtDirection
from .selectors import (
    active_debts_for,
    debt_status_summary,
    get_user_debt,
    totals_by_currency,
)
from .services import apply_repayment, cancel_debt, create_debt

# Mirror UI tab keys (templates use the same strings).
LENT_TAB = DebtDirection.LENT.value
BORROWED_TAB = DebtDirection.BORROWED.value


def _tab_context(user, direction: str) -> dict:
    """Build the list-payload for one tab (debts + per-currency totals)."""
    debts = list(active_debts_for(user, direction=direction))
    totals = totals_by_currency(active_debts_for(user, direction=direction))
    return {"debts": debts, "totals": totals, "direction": direction}


@require_GET
def debts_list_view(request):
    """Render the debts screen with the two tabs ("lent" / "borrowed").

    htmx tab swap: GET /app/debts/?tab=lent with HX-Request returns just the
    tab partial. Full-page nav renders the whole shell.
    """
    tab = request.GET.get("tab") or LENT_TAB
    if tab not in (LENT_TAB, BORROWED_TAB):
        tab = LENT_TAB

    ctx = {
        "active_tab": tab,
        "lent": _tab_context(request.user, LENT_TAB),
        "borrowed": _tab_context(request.user, BORROWED_TAB),
        "summary": debt_status_summary(request.user),
    }

    template = (
        "debts/_tab.html"
        if request.headers.get("HX-Request") and "tab" in request.GET
        else "debts/list.html"
    )
    return render(request, template, ctx)


@require_http_methods(["GET", "POST"])
def debt_create_view(request):
    """Manual debt creation form (fallback to voice; voice hook is Story 4.2)."""
    if request.method == "POST":
        form = DebtCreateForm(request.POST)
        if form.is_valid():
            create_debt(
                user=request.user,
                direction=form.cleaned_data["direction"],
                counterparty=form.cleaned_data["counterparty"],
                amount=form.cleaned_data["amount"],
                currency=form.cleaned_data["currency"],
                expected_return_date=form.cleaned_data.get("expected_return_date"),
                note=form.cleaned_data.get("note") or "",
            )
            response = HttpResponse(status=200)
            response.headers["HX-Redirect"] = reverse("debts:list")
            response.headers["HX-Trigger"] = json.dumps(
                {"toast": {"type": "success", "message": "Qarz qo'shildi."}}
            )
            return response
        response = render(request, "debts/create.html", {"form": form})
        response.status_code = 422
        return response

    form = DebtCreateForm(initial={"direction": LENT_TAB, "currency": "UZS"})
    return render(request, "debts/create.html", {"form": form})


@require_GET
def debt_close_form_view(request, debt_id: int):
    """Render the bottom-sheet close/repay form for one debt.

    Hit via htmx GET so the form swaps into the page without a full reload.
    """
    debt = get_user_debt(request.user, debt_id)
    if debt is None:
        raise Http404("Debt not found")

    form = DebtRepayForm(initial={"amount": debt.remaining_amount})
    return render(request, "debts/_close_form.html", {"form": form, "debt": debt})


@require_POST
def debt_repay_view(request, debt_id: int):
    """Apply a (partial or full) repayment. htmx swap returns the new row."""
    debt = get_user_debt(request.user, debt_id)
    if debt is None:
        raise Http404("Debt not found")

    form = DebtRepayForm(request.POST)
    if not form.is_valid():
        response = render(
            request,
            "debts/_close_form.html",
            {"form": form, "debt": debt},
        )
        response.status_code = 422
        return response

    repaid_on = form.cleaned_data.get("repaid_on")
    repaid_at = (
        timezone.make_aware(datetime.combine(repaid_on, time(12, 0)))
        if repaid_on
        else timezone.now()
    )

    try:
        debt, _ = apply_repayment(
            debt=debt,
            amount=form.cleaned_data["amount"],
            repaid_at=repaid_at,
            note=form.cleaned_data.get("note") or "",
        )
    except RepaymentExceedsRemainingError as exc:
        form.add_error("amount", str(exc))
        response = render(
            request,
            "debts/_close_form.html",
            {"form": form, "debt": debt},
        )
        response.status_code = 422
        return response
    except (DebtAlreadyClosedError, CurrencyMismatchError, InvalidDebtAmountError) as exc:
        response = HttpResponse(status=422)
        response.headers["HX-Trigger"] = json.dumps(
            {"toast": {"type": "error", "message": str(exc)}}
        )
        return response

    closed = debt.state == "closed"
    message = (
        "Qarz yopildi. Rahmat!"
        if closed
        else f"Qisman qaytarildi. Qoldiq: {debt.remaining_amount} {debt.currency}"
    )

    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("debts:list") + f"?tab={debt.direction}"
    response.headers["HX-Trigger"] = json.dumps({"toast": {"type": "success", "message": message}})
    return response


@require_POST
def debt_cancel_view(request, debt_id: int):
    """Forgive / void the debt (state -> cancelled). Already-cancelled returns 410."""
    debt = get_user_debt(request.user, debt_id)
    if debt is None:
        raise Http404("Debt not found")

    reason = (request.POST.get("reason") or "forgiven").strip()
    try:
        debt = cancel_debt(debt=debt, reason=reason)
    except DebtAlreadyClosedError as exc:
        response = HttpResponse(status=410)
        response.headers["HX-Trigger"] = json.dumps(
            {"toast": {"type": "error", "message": str(exc)}}
        )
        return response

    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("debts:list") + f"?tab={debt.direction}"
    response.headers["HX-Trigger"] = json.dumps(
        {"toast": {"type": "info", "message": "Qarz bekor qilindi (kechirildi)."}}
    )
    return response


@require_GET
def debt_detail_view(request, debt_id: int):
    """Timeline view per debt: original + repayments + final close (Story 4.4 AC)."""
    debt = get_user_debt(request.user, debt_id)
    if debt is None:
        raise Http404("Debt not found")

    repayments = list(debt.repayments.order_by("repaid_at", "created_at"))
    return render(
        request,
        "debts/detail.html",
        {"debt": debt, "repayments": repayments},
    )
