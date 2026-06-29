"""Qarzlar screen — v0.7 simplified.

The Qarzlar tab is a filtered view of the Transactions table: rows where
type='debt_lent' ("Menga qarzdor") or 'debt_borrowed' ("Men qarzdorman").

There are 3 endpoints:
- list (GET) — the two-tab screen
- new  (POST) — quick inline-sheet creation, just counterparty + amount + currency
- settle (POST) — flips `settled_at` and spawns the matching cash row
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from currencies.constants import CURRENCY_CODES
from transactions.exceptions import InvalidAmountError, TransactionNotEditableError
from transactions.models import Transaction
from transactions.services import create_transaction, settle_debt_transaction

# UI tab keys mirror the Transaction.type values.
LENT_TAB = "debt_lent"
BORROWED_TAB = "debt_borrowed"
VALID_TABS = (LENT_TAB, BORROWED_TAB)


def _tab_transactions(user, tx_type: str) -> list[Transaction]:
    """Live debt-type transactions for the given user + direction (newest first)."""
    return list(Transaction.objects.for_user(user).filter(type=tx_type).order_by("-date", "-id"))


@require_GET
def debts_list_view(request):
    """Render the two-tab Qarzlar screen."""
    tab = request.GET.get("tab") or LENT_TAB
    if tab not in VALID_TABS:
        tab = LENT_TAB
    return render(
        request,
        "debts/list.html",
        {
            "active_tab": tab,
            "transactions": _tab_transactions(request.user, tab),
        },
    )


def _err(message: str, status: int = 422) -> HttpResponse:
    response = HttpResponse(status=status)
    response.headers["HX-Trigger"] = json.dumps({"toast": {"type": "error", "message": message}})
    return response


def _ok_redirect(tab: str, message: str) -> HttpResponse:
    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("debts:list") + f"?tab={tab}"
    response.headers["HX-Trigger"] = json.dumps({"toast": {"type": "success", "message": message}})
    return response


@require_POST
def new_debt_view(request):
    """Minimal create — counterparty + amount + currency, direction from active tab."""
    tab = (request.POST.get("tab") or LENT_TAB).strip()
    if tab not in VALID_TABS:
        return _err("Yo'nalish noto'g'ri")

    counterparty = (request.POST.get("counterparty") or "").strip()
    if not counterparty:
        return _err("Kim bilan ekanini yozing")

    currency = (request.POST.get("currency") or "UZS").upper()
    if currency not in CURRENCY_CODES:
        return _err("Valyuta noto'g'ri")

    try:
        amount = Decimal(str(request.POST.get("amount") or "0"))
    except (InvalidOperation, ValueError):
        return _err("Summa noto'g'ri")
    if amount <= 0:
        return _err("Summa musbat bo'lishi kerak")

    create_transaction(
        user=request.user,
        type=tab,
        amount=amount,
        currency=currency,
        date=timezone.localdate(),
        counterparty=counterparty,
        note="",
    )
    return _ok_redirect(tab, "Qarz qo'shildi")


@require_POST
def settle_debt_view(request, tx_id: int):
    """Mark the debt-type Transaction as settled + spawn the counter cash row."""
    tx = Transaction.objects.for_user(request.user).filter(pk=tx_id, type__in=VALID_TABS).first()
    if tx is None:
        raise Http404("Qarz topilmadi")

    try:
        settled, _counter = settle_debt_transaction(tx=tx)
    except (InvalidAmountError, TransactionNotEditableError) as exc:
        return _err(str(exc))

    label = "Qarz qaytarib oldim" if settled.type == LENT_TAB else "Qarz qaytarib berdim"
    return _ok_redirect(settled.type, f"{label} · saqlandi")
