"""Qarzlar screen — v0.7 simplified.

There is no separate Debt aggregate any more. The Qarzlar tab is a
filtered view of the Transactions table: rows where type='debt_lent'
("Menga qarzdor") or type='debt_borrowed' ("Men qarzdorman"). Adding a
new entry just opens the standard Add transaction page with the type
pre-selected.
"""

from __future__ import annotations

from django.shortcuts import render
from django.views.decorators.http import require_GET

from transactions.models import Transaction

# UI tab keys mirror the Transaction.type values.
LENT_TAB = "debt_lent"
BORROWED_TAB = "debt_borrowed"


def _tab_transactions(user, tx_type: str) -> list[Transaction]:
    """Live debt-type transactions for the given user + direction."""
    return list(
        Transaction.objects.for_user(user)
        .filter(type=tx_type)
        .select_related("category")
        .order_by("-date", "-id")
    )


@require_GET
def debts_list_view(request):
    """Render the two-tab Qarzlar screen.

    Tabs are server-rendered with a plain `<a href>` (no htmx swap) so the
    active state always matches the URL — same pattern as the History page.
    """
    tab = request.GET.get("tab") or LENT_TAB
    if tab not in (LENT_TAB, BORROWED_TAB):
        tab = LENT_TAB

    return render(
        request,
        "debts/list.html",
        {
            "active_tab": tab,
            "transactions": _tab_transactions(request.user, tab),
        },
    )
